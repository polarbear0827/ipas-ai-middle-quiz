export const STORAGE_KEY = "ipas-ai-middle-quiz-state-v1";

export const LETTERS = ["A", "B", "C", "D"];

export function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultState();
    return { ...defaultState(), ...JSON.parse(raw) };
  } catch {
    return defaultState();
  }
}

export function defaultState() {
  return {
    attempts: {},
    history: [],
    bookmarks: {},
    mode: "quick",
    subjects: ["S1", "S3"],
    examIds: ["114-2", "115-1"],
    search: "",
    activeId: null,
    mock: null,
  };
}

export function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function summarizeProgress(questions, state) {
  const answered = questions.filter((q) => state.attempts[q.id]?.attempts > 0);
  const totalCorrect = answered.reduce((sum, q) => sum + (state.attempts[q.id]?.correct || 0), 0);
  const totalAttempts = answered.reduce((sum, q) => sum + (state.attempts[q.id]?.attempts || 0), 0);
  const streak = computeStreak(state.history);

  return {
    total: questions.length,
    answered: answered.length,
    totalAttempts,
    accuracy: totalAttempts ? Math.round((totalCorrect / totalAttempts) * 100) : 0,
    streak,
    reviewCount: Object.values(state.bookmarks).filter(Boolean).length,
    wrongCount: questions.filter((q) => (state.attempts[q.id]?.wrong || 0) > 0).length,
  };
}

export function computeStreak(history) {
  let streak = 0;
  for (let i = history.length - 1; i >= 0; i -= 1) {
    if (!history[i].correct) break;
    streak += 1;
  }
  return streak;
}

export function filterQuestions(questions, state) {
  const term = state.search.trim().toLowerCase();
  return questions.filter((q) => {
    if (!state.subjects.includes(q.source.subject)) return false;
    if (!state.examIds.includes(q.source.examId)) return false;
    if (!term) return true;
    const haystack = [
      q.id,
      q.prompt,
      q.topic,
      q.source.examLabel,
      q.source.subjectName,
      ...Object.values(q.options),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(term);
  });
}

export function poolByMode(questions, state) {
  const filtered = filterQuestions(questions, state);
  if (state.mode === "wrong") {
    const wrong = filtered.filter((q) => (state.attempts[q.id]?.wrong || 0) > 0 || state.bookmarks[q.id]);
    return wrong.length ? wrong : filtered;
  }
  return filtered;
}

export function weightedPick(questions, state, currentId) {
  const pool = questions.filter((q) => q.id !== currentId);
  if (!pool.length) return questions[0] || null;
  const weighted = pool.map((q) => {
    const attempt = state.attempts[q.id];
    const unseen = attempt?.attempts ? 0 : 8;
    const wrong = attempt?.wrong || 0;
    const correct = attempt?.correct || 0;
    const weak = wrong ? 4 + wrong * 2 - correct : 0;
    const review = state.bookmarks[q.id] ? 3 : 0;
    const figurePenalty = q.hasFigureReference ? -1 : 0;
    return { q, weight: Math.max(1, unseen + weak + review + figurePenalty) };
  });
  const total = weighted.reduce((sum, item) => sum + item.weight, 0);
  let needle = Math.random() * total;
  for (const item of weighted) {
    needle -= item.weight;
    if (needle <= 0) return item.q;
  }
  return weighted[0].q;
}

export function recordAttempt(state, question, choice) {
  const correct = choice === question.answer;
  const previous = state.attempts[question.id] || { attempts: 0, correct: 0, wrong: 0 };
  return {
    ...state,
    attempts: {
      ...state.attempts,
      [question.id]: {
        ...previous,
        attempts: previous.attempts + 1,
        correct: previous.correct + (correct ? 1 : 0),
        wrong: previous.wrong + (correct ? 0 : 1),
        lastAnswer: choice,
        lastCorrect: correct,
        lastAt: new Date().toISOString(),
      },
    },
    history: [
      ...state.history.slice(-799),
      {
        id: question.id,
        subject: question.source.subject,
        topic: question.topic,
        correct,
        at: new Date().toISOString(),
      },
    ],
  };
}

export function topicWeakness(questions, state) {
  const rows = new Map();
  for (const q of questions) {
    const attempt = state.attempts[q.id];
    if (!attempt?.attempts) continue;
    const row = rows.get(q.topic) || { topic: q.topic, attempts: 0, wrong: 0, correct: 0 };
    row.attempts += attempt.attempts;
    row.wrong += attempt.wrong || 0;
    row.correct += attempt.correct || 0;
    rows.set(q.topic, row);
  }
  return [...rows.values()]
    .map((row) => ({
      ...row,
      wrongRate: row.attempts ? Math.round((row.wrong / row.attempts) * 100) : 0,
    }))
    .filter((row) => row.attempts >= 1 && row.wrong > 0)
    .sort((a, b) => b.wrongRate - a.wrongRate || b.attempts - a.attempts)
    .slice(0, 5);
}

export function daysUntil(dateString) {
  const now = new Date();
  const target = new Date(`${dateString}T09:00:00+08:00`);
  return Math.ceil((target.getTime() - now.getTime()) / 86400000);
}

export function makeMock(questions, count = 50) {
  const shuffled = [...questions].sort(() => Math.random() - 0.5);
  return {
    active: true,
    finished: false,
    ids: shuffled.slice(0, Math.min(count, shuffled.length)).map((q) => q.id),
    index: 0,
    answers: {},
    startedAt: Date.now(),
    durationSec: 90 * 60,
  };
}

export function pdfUrlFor(question, baseUrl) {
  const encoded = encodeURIComponent(question.source.file);
  return `${baseUrl}question-bank/${encoded}#page=${question.source.page}`;
}
