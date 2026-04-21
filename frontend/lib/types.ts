export type UserProfile = {
  id: number;
  name: string;
  role: string;
  language: string;
  preferences: Record<string, unknown>;
  goals: string[];
  created_at: string;
  updated_at: string;
};

export type Task = {
  id: number;
  title: string;
  domain: string;
  status: string;
  priority: number;
  source: string;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ReflectionEntry = {
  id: number;
  entry_date: string;
  summary: string;
  patterns: string;
  next_actions: string;
  mood: string;
  created_at: string;
  updated_at: string;
};

export type DailyReflectionInput = {
  completed: string[];
  unfinished: string[];
  blockers: string[];
  mood_or_notes: string;
};

export type DailyReflectionSummary = {
  day_summary: string;
  unfinished_items: string[];
  pattern_hints: string[];
  tomorrow_suggestions: string[];
};

export type DailyReflectionRecord = {
  id: number;
  entry_date: string;
  input: DailyReflectionInput;
  summary: DailyReflectionSummary;
  created_at: string;
};

export type DailyReflectionHistoryResponse = {
  items: DailyReflectionRecord[];
};

export type DailyContextInput = {
  tasks: string[];
  meetings: string[];
  blockers: string[];
  priorities: string[];
};

export type DailyPlanStructured = {
  top_priorities: string[];
  recommended_order: string[];
  risks_and_reminders: string[];
  next_actions: string[];
  status_summary: string;
};

export type DailyPlanRecord = {
  id: number;
  plan_date: string;
  context: DailyContextInput;
  plan: DailyPlanStructured;
  created_at: string;
};

export type DailyPlanHistoryResponse = {
  items: DailyPlanRecord[];
};

export type TechnicalAnalysisInput = {
  logs: string;
  errors: string[];
  code_snippets: string[];
  issue_description: string;
};

export type StructuredAnalysisResult = {
  problem_statement: string;
  likely_causes: string[];
  validation_steps: string[];
  fix_options: string[];
  risks: string[];
  follow_up_tasks: string[];
};

export type TechnicalAnalysisOutput = StructuredAnalysisResult;

export type TechnicalAnalysisRecord = {
  id: number;
  analysis_date: string;
  input: TechnicalAnalysisInput;
  output: TechnicalAnalysisOutput;
  created_at: string;
};

export type TechnicalAnalysisHistoryResponse = {
  items: TechnicalAnalysisRecord[];
};

export type NoteEntry = {
  id: number;
  title: string;
  content: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type PromptTemplate = {
  id: number;
  name: string;
  description: string;
  body: string;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type PromptTemplateImportResponse = {
  mode: string;
  imported: number;
  updated: number;
  skipped: number;
  total: number;
};
