from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import WorkflowOrchestration, WorkflowQueueJob, WorkflowStepRun
from app.services.orchestration_queue_service import list_queue_jobs
from app.services.orchestration_service import get_orchestration_metrics, list_orchestrations


def _make_session() -> tuple[Session, object]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return testing_session_local(), engine


def _seed_orchestration(db: Session, *, created_at: datetime, status: str, duration_ms: int) -> int:
    record = WorkflowOrchestration(
        status=status,
        duration_ms=duration_ms,
        entry_source="perf-test",
        subscription_tier="pro",
        request_json='{"ignored":true}',
        result_json=(
            '{"conclusion":"perf summary",'
            '"risks":["perf risk"],'
            '"next_actions":["perf action"]}'
        ),
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(record)
    db.flush()
    for index, agent_type in enumerate(("planner", "analyzer", "reviewer"), start=1):
        db.add(
            WorkflowStepRun(
                orchestration_id=record.id,
                step_name=f"Step {index}",
                agent_type=agent_type,
                status="success",
                input_summary="{}",
                output_summary="ok",
                audit_json=(
                    '{"conclusion":"ok",'
                    '"evidence":"batched",'
                    '"risk":"none",'
                    '"next_action":"continue"}'
                ),
                fallback_action="",
                started_at=created_at,
                finished_at=created_at,
                duration_ms=1,
                created_at=created_at,
            )
        )
    db.commit()
    return record.id


def test_orchestration_history_batches_step_lookup_and_uses_stable_order() -> None:
    db, engine = _make_session()
    try:
        created_at = datetime(2026, 5, 22, 0, 0, 0)
        first_id = _seed_orchestration(db, created_at=created_at, status="success", duration_ms=100)
        second_id = _seed_orchestration(db, created_at=created_at, status="partial_success", duration_ms=200)
        third_id = _seed_orchestration(db, created_at=created_at, status="failed", duration_ms=300)
        step_selects: list[str] = []

        def before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
            if "FROM workflow_step_runs" in statement:
                step_selects.append(statement)

        event.listen(engine, "before_cursor_execute", before_cursor_execute)
        try:
            response = list_orchestrations(db, limit=10)
        finally:
            event.remove(engine, "before_cursor_execute", before_cursor_execute)

        assert [item.id for item in response.items] == [third_id, second_id, first_id]
        assert [len(item.steps) for item in response.items] == [3, 3, 3]
        assert len(step_selects) == 1
    finally:
        db.close()


def test_orchestration_history_can_skip_steps_for_lightweight_dashboard_queries() -> None:
    db, engine = _make_session()
    try:
        _seed_orchestration(db, created_at=datetime(2026, 5, 22, 0, 0, 0), status="success", duration_ms=100)
        step_selects: list[str] = []

        def before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
            if "FROM workflow_step_runs" in statement:
                step_selects.append(statement)

        event.listen(engine, "before_cursor_execute", before_cursor_execute)
        try:
            response = list_orchestrations(db, limit=10, include_steps=False)
        finally:
            event.remove(engine, "before_cursor_execute", before_cursor_execute)

        assert len(response.items) == 1
        assert response.items[0].steps == []
        assert step_selects == []
    finally:
        db.close()


def test_orchestration_metrics_uses_database_aggregate_result() -> None:
    db, _engine = _make_session()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        _seed_orchestration(db, created_at=now, status="success", duration_ms=100)
        _seed_orchestration(db, created_at=now - timedelta(minutes=1), status="partial_success", duration_ms=200)
        _seed_orchestration(db, created_at=now - timedelta(minutes=2), status="failed", duration_ms=300)

        metrics = get_orchestration_metrics(db, days=7)

        assert metrics.total_runs == 3
        assert metrics.weekly_active_orchestrations == 3
        assert metrics.average_duration_ms == 200
        assert metrics.partial_success_rate == 0.3333
    finally:
        db.close()


def test_queue_history_uses_stable_updated_id_order() -> None:
    db, _engine = _make_session()
    try:
        updated_at = datetime(2026, 5, 22, 0, 0, 0)
        for status in ("queued", "running", "succeeded"):
            db.add(
                WorkflowQueueJob(
                    status=status,
                    attempts=1,
                    max_attempts=3,
                    cancel_requested=False,
                    request_json="{}",
                    error_message="",
                    created_at=updated_at,
                    updated_at=updated_at,
                )
            )
        db.commit()

        response = list_queue_jobs(db, limit=10)

        assert [item.id for item in response.items] == [3, 2, 1]
        assert [item.status for item in response.items] == ["succeeded", "running", "queued"]
    finally:
        db.close()
