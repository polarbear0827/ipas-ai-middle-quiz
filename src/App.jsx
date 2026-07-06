import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Bookmark,
  BookmarkCheck,
  CalendarDays,
  Check,
  ChevronDown,
  CircleAlert,
  ClipboardList,
  Download,
  ExternalLink,
  FileText,
  Flame,
  Gauge,
  GraduationCap,
  ListChecks,
  Menu,
  RefreshCcw,
  Search,
  Settings,
  Timer,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import bank from "./data/questions.json";
import {
  LETTERS,
  daysUntil,
  filterQuestions,
  loadState,
  makeMock,
  pdfUrlFor,
  poolByMode,
  recordAttempt,
  saveState,
  summarizeProgress,
  topicWeakness,
  weightedPick,
} from "./lib/quiz";

const QUESTIONS = bank.questions;
const TARGET_DATE = bank.targetExamDate;
const BASE_URL = import.meta.env.BASE_URL || "./";

function App() {
  const [state, setState] = useState(loadState);
  const [showList, setShowList] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const searchRef = useRef(null);

  const filtered = useMemo(() => filterQuestions(QUESTIONS, state), [state]);
  const pool = useMemo(() => poolByMode(QUESTIONS, state), [state]);
  const activeQuestion = useMemo(() => {
    if (state.mode === "mock" && state.mock?.active) {
      const id = state.mock.ids[state.mock.index];
      return QUESTIONS.find((q) => q.id === id) || pool[0] || QUESTIONS[0];
    }
    return QUESTIONS.find((q) => q.id === state.activeId) || pool[0] || QUESTIONS[0];
  }, [pool, state.activeId, state.mock, state.mode]);

  const progress = useMemo(() => summarizeProgress(QUESTIONS, state), [state]);
  const weakness = useMemo(() => topicWeakness(QUESTIONS, state), [state]);
  const activeAttempt = state.attempts[activeQuestion?.id] || null;
  const selectedAnswer =
    state.mode === "mock" && state.mock?.active
      ? state.mock.answers[activeQuestion?.id]
      : activeAttempt?.lastAnswer;
  const isMock = state.mode === "mock" && state.mock?.active;

  useEffect(() => {
    saveState(state);
  }, [state]);

  useEffect(() => {
    if (!state.activeId && pool[0]) {
      setState((current) => ({ ...current, activeId: pool[0].id }));
    }
  }, [pool, state.activeId]);

  useEffect(() => {
    const onKey = (event) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      const key = event.key.toLowerCase();
      if (["1", "2", "3", "4"].includes(key)) {
        const choice = LETTERS[Number(key) - 1];
        if (choice && activeQuestion) handleAnswer(choice);
      }
      if (key === "enter" || key === "arrowright") {
        event.preventDefault();
        goNext();
      }
      if (key === "arrowleft") {
        event.preventDefault();
        goPrevious();
      }
      if (key === "r") {
        event.preventDefault();
        toggleBookmark(activeQuestion.id);
      }
      if (key === "/") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  function patchState(patch) {
    setState((current) => ({ ...current, ...patch }));
  }

  function setMode(mode) {
    setShowAnswer(false);
    if (mode === "mock") {
      const eligible = filtered.length ? filtered : QUESTIONS;
      patchState({ mode, mock: makeMock(eligible, 50), activeId: null });
      return;
    }
    patchState({ mode, mock: null, activeId: pool[0]?.id || QUESTIONS[0].id });
  }

  function handleAnswer(choice) {
    if (!activeQuestion) return;
    if (isMock) {
      setState((current) => ({
        ...current,
        mock: {
          ...current.mock,
          answers: { ...current.mock.answers, [activeQuestion.id]: choice },
        },
      }));
      return;
    }
    setShowAnswer(true);
    setState((current) => recordAttempt(current, activeQuestion, choice));
  }

  function goNext() {
    setShowAnswer(false);
    if (isMock) {
      setState((current) => ({
        ...current,
        mock: { ...current.mock, index: Math.min(current.mock.index + 1, current.mock.ids.length - 1) },
      }));
      return;
    }
    const next = weightedPick(pool, state, activeQuestion?.id);
    if (next) patchState({ activeId: next.id });
  }

  function goPrevious() {
    setShowAnswer(false);
    if (isMock) {
      setState((current) => ({
        ...current,
        mock: { ...current.mock, index: Math.max(current.mock.index - 1, 0) },
      }));
      return;
    }
    const index = pool.findIndex((q) => q.id === activeQuestion?.id);
    const previous = pool[Math.max(0, index - 1)] || pool[0];
    if (previous) patchState({ activeId: previous.id });
  }

  function toggleSubject(subject) {
    const exists = state.subjects.includes(subject);
    const next = exists ? state.subjects.filter((item) => item !== subject) : [...state.subjects, subject];
    patchState({ subjects: next.length ? next : [subject], activeId: null });
  }

  function toggleExam(examId) {
    const exists = state.examIds.includes(examId);
    const next = exists ? state.examIds.filter((item) => item !== examId) : [...state.examIds, examId];
    patchState({ examIds: next.length ? next : [examId], activeId: null });
  }

  function toggleBookmark(id) {
    setState((current) => ({
      ...current,
      bookmarks: { ...current.bookmarks, [id]: !current.bookmarks[id] },
    }));
  }

  function finishMock() {
    if (!state.mock) return;
    const mockQuestions = state.mock.ids.map((id) => QUESTIONS.find((q) => q.id === id)).filter(Boolean);
    let nextState = { ...state, mock: { ...state.mock, finished: true } };
    for (const q of mockQuestions) {
      const choice = state.mock.answers[q.id];
      if (choice) nextState = recordAttempt(nextState, q, choice);
    }
    setState(nextState);
  }

  function resetProgress() {
    const ok = window.confirm("確定清除本機作答紀錄？題庫不會被刪除。");
    if (!ok) return;
    setState({ ...loadState(), attempts: {}, history: [], bookmarks: {}, activeId: QUESTIONS[0].id, mock: null });
  }

  return (
    <div className="app-shell">
      <TopBar
        progress={progress}
        state={state}
        onSearch={(search) => patchState({ search, activeId: null })}
        searchRef={searchRef}
        onReset={resetProgress}
      />

      <aside className="left-rail">
        <SectionTitle icon={<Gauge size={18} />} label="學習進度" />
        <ProgressBlock progress={progress} />

        <SectionTitle icon={<BookOpen size={18} />} label="科目篩選" />
        <RailButton
          active={state.subjects.includes("S1")}
          icon={<BookOpen size={19} />}
          label="科目1"
          meta={`${countBySubject("S1", filtered)}/${countBySubject("S1", QUESTIONS)}`}
          onClick={() => toggleSubject("S1")}
        />
        <RailButton
          active={state.subjects.includes("S3")}
          icon={<BookOpen size={19} />}
          label="科目3"
          meta={`${countBySubject("S3", filtered)}/${countBySubject("S3", QUESTIONS)}`}
          onClick={() => toggleSubject("S3")}
        />

        <SectionTitle icon={<ClipboardList size={18} />} label="題本" />
        <RailButton
          active={state.examIds.includes("114-2")}
          icon={<FileText size={18} />}
          label="114-2"
          meta="100 題"
          onClick={() => toggleExam("114-2")}
        />
        <RailButton
          active={state.examIds.includes("115-1")}
          icon={<FileText size={18} />}
          label="115-1"
          meta="100 題"
          onClick={() => toggleExam("115-1")}
        />

        <SectionTitle icon={<ListChecks size={18} />} label="模式切換" />
        <RailButton
          active={state.mode === "quick"}
          icon={<Flame size={18} />}
          label="快速刷題"
          meta="加權隨機"
          onClick={() => setMode("quick")}
        />
        <RailButton
          active={state.mode === "wrong"}
          icon={<CircleAlert size={18} />}
          label="錯題"
          meta={`${progress.wrongCount}`}
          onClick={() => setMode("wrong")}
        />
        <RailButton
          active={state.mode === "mock"}
          icon={<Timer size={18} />}
          label="模擬考"
          meta="50 題"
          onClick={() => setMode("mock")}
        />

        <div className="target-box">
          <CalendarDays size={20} />
          <div>
            <strong>11月考試</strong>
            <span>{formatDays(daysUntil(TARGET_DATE))}</span>
          </div>
        </div>

        <a className="export-button" href={`${BASE_URL}question-bank/${encodeURIComponent(activeQuestion?.source.file || "")}`} target="_blank" rel="noreferrer">
          <Download size={18} />
          目前題本
        </a>
      </aside>

      <main className="question-stage">
        {activeQuestion ? (
          <>
            <QuestionHeader
              question={activeQuestion}
              index={isMock ? state.mock.index + 1 : filtered.findIndex((q) => q.id === activeQuestion.id) + 1}
              total={isMock ? state.mock.ids.length : filtered.length}
              isMock={isMock}
              mock={state.mock}
              onFinishMock={finishMock}
            />

            {state.mock?.finished ? (
              <MockResult mock={state.mock} questions={QUESTIONS} onRestart={() => setMode("mock")} />
            ) : (
              <QuestionCard
                question={activeQuestion}
                selectedAnswer={selectedAnswer}
                showAnswer={!isMock && (showAnswer || Boolean(activeAttempt?.lastAnswer))}
                isMock={isMock}
                bookmarked={Boolean(state.bookmarks[activeQuestion.id])}
                onAnswer={handleAnswer}
                onToggleBookmark={() => toggleBookmark(activeQuestion.id)}
                onShowAnswer={() => setShowAnswer((value) => !value)}
              />
            )}

            <div className="bottom-actions">
              <button className="ghost-button" type="button" onClick={goPrevious}>
                <ArrowLeft size={19} />
                上一題
              </button>
              <button className="ghost-button center-action" type="button" onClick={() => setShowList(true)}>
                <ListChecks size={19} />
                題目列表
              </button>
              <button className="primary-button" type="button" onClick={goNext}>
                下一題
                <ArrowRight size={19} />
              </button>
            </div>
          </>
        ) : (
          <EmptyState onClear={() => patchState({ search: "", subjects: ["S1", "S3"], examIds: ["114-2", "115-1"] })} />
        )}
      </main>

      <aside className="right-rail">
        <StudyStatus progress={progress} />
        <WeakTopics weakness={weakness} />
        <ReviewQueue questions={QUESTIONS} state={state} onPick={(id) => patchState({ activeId: id, mode: "quick", mock: null })} />
        <SourcePanel question={activeQuestion} />
      </aside>

      {showList ? (
        <QuestionList
          questions={filtered}
          state={state}
          onClose={() => setShowList(false)}
          onPick={(id) => {
            patchState({ activeId: id, mode: "quick", mock: null });
            setShowList(false);
          }}
        />
      ) : null}
    </div>
  );
}

function TopBar({ progress, state, onSearch, searchRef, onReset }) {
  return (
    <header className="topbar">
      <div className="brand">
        <Menu size={24} />
        <span>iPAS AI 中級刷題室</span>
      </div>
      <label className="search-box">
        <Search size={20} />
        <input ref={searchRef} value={state.search} onChange={(event) => onSearch(event.target.value)} placeholder="搜尋題目 / 關鍵字" />
      </label>
      <div className="top-select">
        全部題型
        <ChevronDown size={17} />
      </div>
      <div className="top-stats">
        <Stat label="總題數" value={progress.total} />
        <Stat label="已作答" value={progress.answered} />
        <Stat label="正確率" value={`${progress.accuracy}%`} accent />
        <Stat label="連續正確" value={progress.streak} />
      </div>
      <button className="icon-button" type="button" onClick={onReset} title="清除本機進度">
        <Settings size={21} />
      </button>
    </header>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong className={accent ? "accent-text" : ""}>{value}</strong>
    </div>
  );
}

function SectionTitle({ icon, label }) {
  return (
    <div className="section-title">
      {icon}
      <span>{label}</span>
    </div>
  );
}

function ProgressBlock({ progress }) {
  const pct = progress.total ? Math.round((progress.answered / progress.total) * 100) : 0;
  return (
    <div className="progress-block">
      <div className="spread">
        <span>總進度</span>
        <strong>
          {progress.answered} / {progress.total}
        </strong>
      </div>
      <div className="meter">
        <span style={{ width: `${pct}%` }} />
      </div>
      <div className="spread small">
        <span>完成率</span>
        <span>{pct}%</span>
      </div>
    </div>
  );
}

function RailButton({ active, icon, label, meta, onClick }) {
  return (
    <button className={`rail-button ${active ? "active" : ""}`} type="button" onClick={onClick}>
      <span className="rail-icon">{icon}</span>
      <span>{label}</span>
      <em>{meta}</em>
    </button>
  );
}

function QuestionHeader({ question, index, total, isMock, mock, onFinishMock }) {
  return (
    <div className="question-header">
      <div className="source-row">
        <span className="source-tag">來源：{question.source.examLabel}</span>
        <span>{question.source.subjectName}</span>
        {question.hasFigureReference ? <span className="warn-tag">附圖題</span> : null}
      </div>
      <div className="question-count">
        {isMock ? (
          <>
            <Timer size={17} />
            {mock.index + 1} / {mock.ids.length}
            <button type="button" className="finish-button" onClick={onFinishMock}>
              交卷
            </button>
          </>
        ) : (
          <>
            第 {Math.max(index, 1)} 題 / 共 {total} 題
          </>
        )}
      </div>
    </div>
  );
}

function QuestionCard({ question, selectedAnswer, showAnswer, isMock, bookmarked, onAnswer, onToggleBookmark, onShowAnswer }) {
  const correct = question.answer;
  const answered = Boolean(selectedAnswer);

  return (
    <section className="question-card">
      <div className="question-meta">
        <span>{question.topic}</span>
        <span>單選題</span>
        <span>{question.id}</span>
      </div>
      <h1>{question.prompt}</h1>
      {question.hasFigureReference ? (
        <div className="figure-alert">
          <CircleAlert size={18} />
          這題引用 PDF 圖表或程式碼，作答後可開原題頁核對。
        </div>
      ) : null}
      <div className="options">
        {LETTERS.map((letter) => {
          const isSelected = selectedAnswer === letter;
          const isCorrect = showAnswer && correct === letter;
          const isWrong = showAnswer && isSelected && selectedAnswer !== correct;
          return (
            <button
              key={letter}
              type="button"
              className={`option-row ${isSelected ? "selected" : ""} ${isCorrect ? "correct" : ""} ${isWrong ? "wrong" : ""}`}
              onClick={() => onAnswer(letter)}
            >
              <span className="choice-dot">{isCorrect ? <Check size={17} /> : letter}</span>
              <span>{question.options[letter]}</span>
            </button>
          );
        })}
      </div>

      {!isMock && answered ? (
        <div className={`feedback ${selectedAnswer === correct ? "good" : "bad"}`}>
          <div className="feedback-title">
            {selectedAnswer === correct ? <Check size={20} /> : <X size={20} />}
            <strong>{selectedAnswer === correct ? "答對了" : `答錯了，正解是 ${correct}`}</strong>
          </div>
          <p>{buildHint(question)}</p>
          <div className="feedback-links">
            <a href={pdfUrlFor(question, BASE_URL)} target="_blank" rel="noreferrer">
              <ExternalLink size={17} />
              開原題頁
            </a>
            <button type="button" onClick={onToggleBookmark}>
              {bookmarked ? <BookmarkCheck size={17} /> : <Bookmark size={17} />}
              {bookmarked ? "已加入複習" : "加入複習"}
            </button>
          </div>
        </div>
      ) : null}

      <div className="question-tools">
        <button className="ghost-button compact" type="button" onClick={onToggleBookmark}>
          {bookmarked ? <BookmarkCheck size={17} /> : <Bookmark size={17} />}
          {bookmarked ? "已標記" : "標記複習"}
        </button>
        <button className="ghost-button compact" type="button" onClick={onShowAnswer} disabled={isMock}>
          <FileText size={17} />
          看解析
        </button>
        <a className="ghost-link compact" href={pdfUrlFor(question, BASE_URL)} target="_blank" rel="noreferrer">
          <ExternalLink size={17} />
          原始 PDF
        </a>
      </div>
    </section>
  );
}

function buildHint(question) {
  const answerText = question.options[question.answer];
  return `官方公告題本未附逐題解析。先記這題的定位：${question.topic}；正確選項重點是「${answerText}」。`;
}

function StudyStatus({ progress }) {
  return (
    <section className="side-panel">
      <h2>學習狀態</h2>
      <div className="status-grid">
        <div>
          <span>連續正確</span>
          <strong>
            {progress.streak}
            <Flame size={24} />
          </strong>
        </div>
        <div>
          <span>正確率</span>
          <strong className="accent-text">{progress.accuracy}%</strong>
        </div>
      </div>
      <div className="mini-row">
        <span>作答次數</span>
        <strong>{progress.totalAttempts}</strong>
      </div>
      <div className="mini-row">
        <span>錯題</span>
        <strong>{progress.wrongCount}</strong>
      </div>
      <div className="mini-row">
        <span>待複習</span>
        <strong>{progress.reviewCount}</strong>
      </div>
    </section>
  );
}

function WeakTopics({ weakness }) {
  return (
    <section className="side-panel">
      <h2>弱點科目 TOP</h2>
      {weakness.length ? (
        <ol className="weak-list">
          {weakness.slice(0, 3).map((row) => (
            <li key={row.topic}>
              <span>{row.topic}</span>
              <strong>{row.wrongRate}%</strong>
            </li>
          ))}
        </ol>
      ) : (
        <p className="muted">先作答幾題，這裡會開始排序。</p>
      )}
    </section>
  );
}

function ReviewQueue({ questions, state, onPick }) {
  const items = questions.filter((q) => state.bookmarks[q.id]).slice(0, 5);
  return (
    <section className="side-panel">
      <h2>待複習清單</h2>
      {items.length ? (
        <div className="review-list">
          {items.map((q) => (
            <button key={q.id} type="button" onClick={() => onPick(q.id)}>
              <span>{q.topic}</span>
              <strong>{q.id}</strong>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">遇到易錯題就標記起來。</p>
      )}
    </section>
  );
}

function SourcePanel({ question }) {
  if (!question) return null;
  return (
    <section className="side-panel">
      <h2>題源</h2>
      <div className="source-detail">
        <span>{question.source.examLabel}</span>
        <strong>{question.source.subjectName}</strong>
        <a href={pdfUrlFor(question, BASE_URL)} target="_blank" rel="noreferrer">
          第 {question.source.page} 頁
          <ExternalLink size={16} />
        </a>
      </div>
    </section>
  );
}

function MockResult({ mock, questions, onRestart }) {
  const rows = mock.ids.map((id) => {
    const q = questions.find((item) => item.id === id);
    return { q, choice: mock.answers[id], correct: q?.answer === mock.answers[id] };
  });
  const answered = rows.filter((row) => row.choice);
  const correct = rows.filter((row) => row.correct).length;
  const score = rows.length ? Math.round((correct / rows.length) * 100) : 0;

  return (
    <section className="result-panel">
      <GraduationCap size={44} />
      <h1>模擬考完成</h1>
      <div className="score-line">
        <strong>{score}</strong>
        <span>分</span>
      </div>
      <p>
        已作答 {answered.length} / {rows.length} 題，答對 {correct} 題。
      </p>
      <button className="primary-button" type="button" onClick={onRestart}>
        <RefreshCcw size={18} />
        再跑一回
      </button>
    </section>
  );
}

function QuestionList({ questions, state, onClose, onPick }) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="question-list-modal">
        <div className="modal-head">
          <h2>題目列表</h2>
          <button className="icon-button" type="button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="question-grid">
          {questions.map((q) => {
            const attempt = state.attempts[q.id];
            const status = attempt?.lastCorrect ? "ok" : attempt?.wrong ? "miss" : "";
            return (
              <button key={q.id} className={status} type="button" onClick={() => onPick(q.id)}>
                <span>
                  {q.source.examId} {q.source.subject === "S1" ? "科1" : "科3"}
                </span>
                <strong>{String(q.number).padStart(2, "0")}</strong>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onClear }) {
  return (
    <section className="empty-state">
      <Search size={38} />
      <h1>找不到符合條件的題目</h1>
      <button className="primary-button" type="button" onClick={onClear}>
        清除篩選
      </button>
    </section>
  );
}

function countBySubject(subject, questions) {
  return questions.filter((q) => q.source.subject === subject).length;
}

function formatDays(days) {
  if (days > 0) return `剩餘 ${days} 天`;
  if (days === 0) return "就是今天";
  return "考期已過";
}

export default App;
