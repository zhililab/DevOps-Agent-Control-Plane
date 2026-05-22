const steps = ["Plan", "Analyze", "Review", "Bill"];

export function ProductDemoMotion() {
  return (
    <aside className="product-demo-motion" aria-label="Animated DevOps workflow preview">
      <div className="demo-terminal">
        <div className="demo-window-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <p className="demo-line demo-line-one">
          <span>input</span>
          <strong>release gate + incident context</strong>
        </p>
        <p className="demo-line demo-line-two">
          <span>policy</span>
          <strong>power tier approval required</strong>
        </p>
        <p className="demo-line demo-line-three">
          <span>ledger</span>
          <strong>6 events verified</strong>
        </p>
      </div>
      <div className="demo-step-flow">
        {steps.map((step, index) => (
          <div className="demo-step-node" style={{ ["--step-index" as string]: index }} key={step}>
            <span>{step}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
