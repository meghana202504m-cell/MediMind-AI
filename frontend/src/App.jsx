import { useEffect, useRef, useState } from "react";
import "./App.css";
import {
  chat,
  getPatientDashboard,
  getPatientInsights,
  getPatientRisks,
  getPatientTrends,
  listReports,
  uploadDocument,
} from "./services/api";
import { useVoiceAssistant } from "./hooks/useVoiceAssistant";

const THOUGHTS = [
  "Small healthy habits, repeated consistently, can make a meaningful difference over time.",
  "Understanding your health numbers is the first step toward informed health decisions.",
  "Regular health checkups can help you notice changes early.",
];

const LANGUAGE_LABELS = { en: "English", kn: "ಕನ್ನಡ", hi: "हिन्दी" };

function formatDate(value) {
  if (!value) return "Date unavailable";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function statusLabel(status) {
  if (!status || status === "unknown") return "Status unavailable";
  if (status === "normal") return "Within range";
  return "Value to review";
}

function MetricCard({ metric }) {
  const hasRange = metric.reference_low !== null && metric.reference_high !== null;
  return (
    <article className="metric-card">
      <div className="metric-card-topline"><span className="metric-name">{metric.biomarker_name}</span><span className={`status-pill ${metric.status || "unknown"}`}>{statusLabel(metric.status)}</span></div>
      <strong className="metric-value">{metric.value ?? "Not recorded"} <small>{metric.unit || ""}</small></strong>
      {hasRange && <span className="metric-range">Report range: {metric.reference_low}–{metric.reference_high} {metric.unit || ""}</span>}
    </article>
  );
}

function EmptyState({ icon, title, text }) {
  return <div className="empty-state"><span className="empty-icon">{icon}</span><strong>{title}</strong><p>{text}</p></div>;
}

function InsightCard({ icon, title, text, warning = false }) {
  return <article className={`insight-card ${warning ? "warning" : ""}`}><span className="insight-icon">{icon}</span><div><h3>{title}</h3><p>{text}</p></div><span className="card-arrow">↗</span></article>;
}

function App() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [documentId, setDocumentId] = useState("");
  const [reportName, setReportName] = useState("");
  const [patientId, setPatientId] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [reports, setReports] = useState([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [insights, setInsights] = useState([]);
  const [risks, setRisks] = useState([]);
  const [trends, setTrends] = useState({});
  const [dataLoading, setDataLoading] = useState(false);
  const [language, setLanguage] = useState(() => localStorage.getItem("medimind-language") || "en");
  const [thoughtIndex, setThoughtIndex] = useState(0);
  const [chatOpen, setChatOpen] = useState(false);
  const fileInputRef = useRef(null);
  const { listening, speaking, supported, voiceMessage, startListening, stopListening, speak, stopSpeaking } = useVoiceAssistant(language, setQuestion);

  useEffect(() => {
    const loadReports = async () => {
      try {
        const data = await listReports();
        setReports(data.reports || []);
      } catch {
        setError("Report history is temporarily unavailable.");
      } finally {
        setReportsLoading(false);
      }
    };
    loadReports();
  }, []);

  useEffect(() => localStorage.setItem("medimind-language", language), [language]);

  useEffect(() => {
    const timer = window.setInterval(() => setThoughtIndex((index) => (index + 1) % THOUGHTS.length), 8000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!patientId) return;
    const loadPatientData = async () => {
      setDataLoading(true);
      try {
        const [dashboardData, insightData, riskData, trendData] = await Promise.all([
          getPatientDashboard(patientId), getPatientInsights(patientId), getPatientRisks(patientId), getPatientTrends(patientId),
        ]);
        setDashboard(dashboardData);
        setInsights(insightData.insights || []);
        setRisks(riskData.risks || []);
        setTrends(trendData.trends || {});
      } catch {
        setError("Health insights are temporarily unavailable.");
      } finally {
        setDataLoading(false);
      }
    };
    loadPatientData();
  }, [patientId]);

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;
    const extension = selectedFile.name.split(".").pop()?.toLowerCase();
    if (!extension || !["pdf", "jpg", "jpeg", "png"].includes(extension)) {
      setError("Please upload a PDF, JPG, JPEG, or PNG file.");
      return;
    }
    setFile(selectedFile);
    setUploaded(false);
    setDocumentId("");
    setPatientId("");
    setReportName("");
    setError("");
  };

  const uploadReport = async () => {
    if (!file) {
      setError("Please select a medical report first.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const data = await uploadDocument(file);
      if (!data.document_id) throw new Error("The report could not be opened.");
      setUploaded(true);
      setChatOpen(true);
      setDocumentId(data.document_id);
      setPatientId(data.patient_id || "");
      setReportName(data.filename || file.name);
      setReports((previous) => [{ report_id: data.report_id, file_hash: data.document_id, source_filename: data.filename || file.name, upload_date: new Date().toISOString(), patient_id: data.patient_id }, ...previous.filter((report) => report.file_hash !== data.document_id)]);
      setMessages([{ role: "assistant", content: "Your report is ready. I can help explain the results simply." }]);
    } catch (err) {
      setError(err.message || "Unable to analyze the report. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const openStoredReport = (report) => {
    if (!report.file_hash) {
      setError("This stored report cannot be opened right now.");
      return;
    }
    setFile(null);
    setUploaded(true);
    setChatOpen(true);
    setDocumentId(report.file_hash);
    setPatientId(report.patient_id || "");
    setReportName(report.source_filename || "Stored medical report");
    setMessages([{ role: "assistant", content: "This report is ready. Ask me about any result or range." }]);
  };

  const askQuestion = async (suggestedQuestion = question) => {
    const trimmedQuestion = suggestedQuestion.trim();
    if (!trimmedQuestion || asking) return;
    setAsking(true);
    setError("");
    setQuestion("");
    setMessages((previous) => [...previous, { role: "user", content: trimmedQuestion, time: new Date() }]);
    try {
      const data = await chat(trimmedQuestion, uploaded ? documentId : null, language);
      const answer = data.answer || data.response || data.message || "I couldn't find an answer to that question.";
      setMessages((previous) => [...previous, { role: "assistant", content: answer, time: new Date() }]);
    } catch (err) {
      setError(err.message || "Unable to connect to MediMind AI. Please try again.");
    } finally {
      setAsking(false);
    }
  };

  const resetReport = () => {
    setFile(null);
    setUploaded(false);
    setChatOpen(false);
    setDocumentId("");
    setPatientId("");
    setReportName("");
    setMessages([]);
    setQuestion("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const latestMetrics = dashboard?.biomarkers || [];
  const visibleRisks = risks.slice(0, 3);
  const hasTrends = Object.keys(trends).length > 0;

  return (
    <div className="app">
      <header className="navbar">
        <button className="brand brand-button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <span className="brand-icon">✚</span><span><strong>MediMind AI</strong><small>Healthcare report companion</small></span>
        </button>
        <nav className="nav-links" aria-label="Primary navigation">
          <button onClick={() => document.getElementById("home")?.scrollIntoView({ behavior: "smooth" })}>Home</button>
          <button onClick={() => document.getElementById("reports")?.scrollIntoView({ behavior: "smooth" })}>Reports</button>
          <button onClick={() => document.getElementById("insights")?.scrollIntoView({ behavior: "smooth" })}>Insights</button>
          <button onClick={() => { setChatOpen(true); document.getElementById("chat")?.scrollIntoView({ behavior: "smooth" }); }}>Chat</button>
        </nav>
        <div className="header-actions"><label className="language-select"><span className="sr-only">Language</span><select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">English</option><option value="kn">ಕನ್ನಡ</option><option value="hi">हिन्दी</option></select></label><span className="status"><i /> Local AI</span></div>
      </header>

      <main className="main-container">
        <section className="hero-panel" id="home">
          <div className="hero-copy"><span className="hero-kicker">Private, clear, report-aware</span><h1>Your reports, <em>explained simply.</em></h1><p>Understand your health reports, ask thoughtful questions, and keep the important numbers in view.</p><div className="hero-actions"><button className="primary-button" onClick={() => fileInputRef.current?.click()}>Upload report <span>↗</span></button><button className="secondary-button" onClick={() => { setChatOpen(true); document.getElementById("chat")?.scrollIntoView({ behavior: "smooth" }); }}>Ask MediMind <span>✦</span></button></div><input ref={fileInputRef} type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => handleFile(event.target.files[0])} hidden /></div>
          <div className="thought-card"><span className="thought-label">Medical thought of the day</span><div className="thought-mark">“</div><p>{THOUGHTS[thoughtIndex]}</p><span className="thought-note">General wellness reflection, not a diagnosis</span></div>
        </section>

        {error && <div className="error-message" role="alert">{error}</div>}

        <section className="section-block" id="reports">
          <div className="section-heading"><div><span className="eyebrow">Your workspace</span><h2>Reports and analysis</h2></div><span className="report-count">{reports.length} saved</span></div>
          <div className="workspace-grid">
            <div className={`upload-card ${dragging ? "is-dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); handleFile(event.dataTransfer.files[0]); }}><div className="upload-card-icon">↥</div><h3>{file ? file.name : "Bring a report into focus"}</h3><p>Drop a PDF or image here, or browse from your device.</p><button className="outline-button" onClick={() => fileInputRef.current?.click()}>Choose report</button>{file && <button className="primary-button compact" onClick={uploadReport} disabled={uploading}>{uploading ? "Analyzing your report..." : "Analyze report"}</button>}<small>PDF, JPG, JPEG, and PNG supported</small></div>
            <div className="history-card"><div className="card-heading"><div><span className="eyebrow">History</span><h3>Recent reports</h3></div><span className="card-icon">◷</span></div>{reportsLoading ? <div className="skeleton-list"><span /><span /><span /></div> : reports.length === 0 ? <EmptyState icon="＋" title="Your health journey starts here." text="Upload your first report to begin understanding your results." /> : <div className="report-list">{reports.slice(0, 5).map((report) => <button className="report-item" key={report.report_id || report.file_hash} onClick={() => openStoredReport(report)}><span className="report-item-icon">▣</span><span className="report-item-details"><strong>{report.source_filename || "Medical report"}</strong><small>{formatDate(report.report_date || report.upload_date)}</small></span><span className="report-item-arrow">→</span></button>)}</div>}</div>
          </div>
          {uploaded && <section className="report-summary"><div className="report-summary-header"><div><span className="eyebrow">Active report</span><h2>{reportName}</h2><p>Uploaded {formatDate(dashboard?.latest_report?.upload_date)}</p></div><button className="ghost-button" onClick={resetReport}>Close report</button></div>{dataLoading ? <p className="loading-copy">Preparing your health insights...</p> : <div className="metrics-grid">{latestMetrics.length ? latestMetrics.slice(0, 6).map((metric) => <MetricCard key={`${metric.biomarker_name}-${metric.report_date}`} metric={metric} />) : <EmptyState icon="⌁" title="No measurements extracted yet." text="Ask MediMind about the report or upload a clearer document." />}</div>}</section>}
        </section>

        <section className="section-block" id="insights"><div className="section-heading"><div><span className="eyebrow">Evidence from your data</span><h2>MediMind insights</h2></div></div><div className="insights-grid"><InsightCard icon="◌" title="Report summary" text={dashboard?.latest_report ? `Latest report: ${formatDate(dashboard.latest_report.report_date || dashboard.latest_report.upload_date)}.` : "Upload a report to generate your health insights."} /><InsightCard icon="▥" title="Key measurements" text={latestMetrics.length ? `${latestMetrics.length} measurements are available from this report.` : "Your extracted measurements will appear here."} /><InsightCard icon="⚠" title="Values to review" text={visibleRisks.length ? `${visibleRisks.length} value${visibleRisks.length === 1 ? "" : "s"} outside the report range.` : "No values to review from the available report data."} warning={visibleRisks.length > 0} /><InsightCard icon="↗" title="Trends" text={hasTrends ? `${Object.keys(trends).length} tracked measurement${Object.keys(trends).length === 1 ? "" : "s"} across your history.` : "Upload multiple reports over time to explore your health trends."} /></div>{(insights.length > 0 || visibleRisks.length > 0) && <div className="insight-feed">{insights.map((insight) => <div className="feed-item" key={`${insight.type}-${insight.message}`}><span>✦</span><p>{insight.message}</p></div>)}{visibleRisks.map((risk) => <div className="feed-item caution" key={`${risk.biomarker_name}-${risk.report_date}`}><span>!</span><p>{risk.biomarker_name}: consider discussing this result with a healthcare professional.</p></div>)}</div>}</section>

        {chatOpen && <section className="chat-section section-block" id="chat"><div className="section-heading"><div><span className="eyebrow">Your questions, answered</span><h2>Chat with MediMind</h2></div><span className="chat-language">{LANGUAGE_LABELS[language]}</span></div><div className="chat-card"><div className="chat-header"><div className="ai-avatar">✦</div><div><h3>MediMind Insight</h3><span>{uploaded ? `Discussing ${reportName}` : "General medical education"}</span></div></div><div className="messages">{messages.length === 0 && <EmptyState icon="✦" title="What would you like to understand?" text={uploaded ? "Ask about a result, its report range, or the big picture." : "Ask a general medical question or upload a report for context."} />}{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`message-row ${message.role}`}><div className="message-content"><div className="message-meta"><span>{message.role === "assistant" ? "MediMind Insight" : "You"}</span>{message.time && <time>{message.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>}</div><div className="message-bubble">{message.content}</div>{message.role === "assistant" && <button className="speak-button" onClick={() => speaking ? stopSpeaking() : speak(message.content)}>{speaking ? "■ Stop speaking" : "◖ Listen"}</button>}</div></div>)}{asking && <div className="message-row assistant"><div className="message-avatar">✦</div><div className="message-bubble typing"><span /><span /><span /></div></div>}</div><div className="suggestions"><span>Suggested questions</span><button onClick={() => askQuestion("What does my fasting blood sugar mean?")}>Explain a result</button><button onClick={() => askQuestion("Which values are outside the report range?")}>Review ranges</button><button onClick={() => askQuestion("Explain this report simply")}>Simple summary</button></div><div className="question-box"><button className={`voice-button ${listening ? "is-listening" : ""}`} onClick={listening ? stopListening : startListening} disabled={!supported} aria-label={listening ? "Stop listening" : "Start voice input"}>{listening ? "●" : "♩"}</button><textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); askQuestion(); } }} placeholder={listening ? "Listening..." : "Ask a question about your health report..."} rows="1" disabled={asking} /><button onClick={() => askQuestion()} disabled={!question.trim() || asking} className="send-button" aria-label="Send question">➤</button></div>{(voiceMessage || !supported) && <p className="voice-note">{voiceMessage || "Voice input is not supported in this browser. You can type your question instead."}</p>}<p className="medical-disclaimer">MediMind AI provides educational explanations of health reports and does not replace professional medical advice.</p></div></section>}
      </main>
      <footer><p>Local-first health education, designed around your report.</p></footer>
    </div>
  );
}

export default App;
