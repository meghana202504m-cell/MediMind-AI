import { useState, useRef } from "react";
import "./App.css";
import { chat, uploadDocument } from "./services/api";

function App() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [documentId, setDocumentId] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  const fileInputRef = useRef(null);

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;

    const allowedTypes = ["pdf", "jpg", "jpeg", "png"];
    const extension = selectedFile.name.split(".").pop()?.toLowerCase();

    if (!extension || !allowedTypes.includes(extension)) {
      setError("Please upload a PDF, JPG, JPEG, or PNG file.");
      return;
    }

    setFile(selectedFile);
    setUploaded(false);
    setDocumentId("");
    setMessages([]);
    setError("");
  };

  const handleFileChange = (event) => {
    handleFile(event.target.files[0]);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);

    const droppedFile = event.dataTransfer.files[0];
    handleFile(droppedFile);
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
      if (!data.document_id) {
        throw new Error("The report was processed but no report ID was returned.");
      }

      setUploaded(true);
      setDocumentId(data.document_id);

      setMessages([
        {
          role: "assistant",
          content:
            data.message ||
            "Your medical report has been processed successfully. You can now ask questions about it.",
        },
      ]);
    } catch (err) {
      setError(
        err.message || "Unable to upload the report. Please try again."
      );
    } finally {
      setUploading(false);
    }
  };

  const askQuestion = async () => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) return;

    setAsking(true);
    setError("");

    const userMessage = {
      role: "user",
      content: trimmedQuestion,
    };

    setMessages((previous) => [...previous, userMessage]);
    setQuestion("");

    try {
      const data = await chat(trimmedQuestion, uploaded ? documentId : null);

      const answer =
        data.answer ||
        data.response ||
        data.message ||
        "I couldn't find an answer to that question.";

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: answer,
        },
      ]);
    } catch (err) {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            "Sorry, I couldn't process your question. Please try again.",
        },
      ]);

      setError(err.message || "Something went wrong.");
    } finally {
      setAsking(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      askQuestion();
    }
  };

  const resetReport = () => {
    setFile(null);
    setUploaded(false);
    setDocumentId("");
    setMessages([]);
    setQuestion("");
    setError("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="app">
      {/* Navbar */}
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">✚</div>

          <div>
            <h1>MediMind AI</h1>
            <span>Healthcare Report Assistant</span>
          </div>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          AI Assistant
        </div>
      </header>

      <main className="main-container">
        {/* Hero */}
        {!uploaded && (
          <section className="hero">
            <div className="hero-badge">
              🩺 AI-Powered Healthcare Assistant
            </div>

            <h2>
              Understand your
              <span> medical reports </span>
              easily.
            </h2>

            <p>
              Upload your medical report and ask questions in simple
              language. MediMind AI helps you understand the information
              contained in your report.
            </p>
          </section>
        )}

        {/* Upload Section */}
        {!uploaded && (
          <section className="upload-card">
            <div
              className={`drop-zone ${dragging ? "dragging" : ""}`}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                hidden
              />

              <div className="upload-icon">📄</div>

              <h3>
                {file
                  ? file.name
                  : "Upload your medical report"}
              </h3>

              <p>
                Drag & drop your report here or click to browse
              </p>

              <small>
                Supported formats: PDF, JPG, JPEG, PNG
              </small>
            </div>

            {file && (
              <div className="selected-file">
                <div className="file-info">
                  <div className="file-icon">
                    {file.type === "application/pdf" ? "📕" : "🖼️"}
                  </div>

                  <div>
                    <strong>{file.name}</strong>
                    <span>
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                </div>

                <button
                  className="remove-button"
                  onClick={(event) => {
                    event.stopPropagation();
                    resetReport();
                  }}
                >
                  ✕
                </button>
              </div>
            )}

            {error && <div className="error-message">{error}</div>}

            <button
              className="upload-button"
              onClick={uploadReport}
              disabled={!file || uploading}
            >
              {uploading ? (
                <>
                  <span className="spinner"></span>
                  Processing report...
                </>
              ) : (
                <>🔍 Analyze Report</>
              )}
            </button>

            <p className="privacy-note">
              🔒 Your report is processed securely for analysis.
            </p>
          </section>
        )}

        {/* Chat Section */}
        {uploaded && (
          <section className="chat-section">
            {/* Report header */}
            <div className="report-header">
              <div className="report-details">
                <div className="success-icon">✓</div>

                <div>
                  <h3>Report Ready</h3>
                  <p>{file?.name}</p>
                </div>
              </div>

              <button
                className="new-report-button"
                onClick={resetReport}
              >
                + New Report
              </button>
            </div>

            {/* Chat */}
            <div className="chat-card">
              <div className="chat-header">
                <div className="ai-avatar">✦</div>

                <div>
                  <h3>MediMind AI</h3>
                  <span>Ask anything about your report</span>
                </div>
              </div>

              <div className="messages">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`message-row ${message.role}`}
                  >
                    {message.role === "assistant" && (
                      <div className="message-avatar">✦</div>
                    )}

                    <div className="message-bubble">
                      {message.content}
                    </div>
                  </div>
                ))}

                {asking && (
                  <div className="message-row assistant">
                    <div className="message-avatar">✦</div>

                    <div className="message-bubble typing">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                )}
              </div>

              {/* Suggestions */}
              <div className="suggestions">
                <span>Try asking:</span>

                <button
                  onClick={() =>
                    setQuestion("What are my important test results?")
                  }
                >
                  Important results
                </button>

                <button
                  onClick={() =>
                    setQuestion("What does my HbA1c level mean?")
                  }
                >
                  Explain HbA1c
                </button>

                <button
                  onClick={() =>
                    setQuestion("Are there any values outside the reference range?")
                  }
                >
                  Abnormal values
                </button>

                <button
                  onClick={() =>
                    setQuestion("Can you explain my report in simple terms?")
                  }
                >
                  Simple explanation
                </button>
              </div>

              {/* Input */}
              <div className="question-box">
                <textarea
                  value={question}
                  onChange={(event) =>
                    setQuestion(event.target.value)
                  }
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about your medical report..."
                  rows="1"
                  disabled={asking}
                />

                <button
                  onClick={askQuestion}
                  disabled={!question.trim() || asking}
                  className="send-button"
                >
                  ➤
                </button>
              </div>

              <p className="medical-disclaimer">
                MediMind AI provides informational assistance and does not
                replace professional medical advice.
              </p>
            </div>
          </section>
        )}

        {/* Features */}
        {!uploaded && (
          <section className="features">
            <div className="feature">
              <div className="feature-icon">📄</div>
              <h3>Multiple Formats</h3>
              <p>
                Upload PDF reports or scanned medical images.
              </p>
            </div>

            <div className="feature">
              <div className="feature-icon">🔍</div>
              <h3>Smart Extraction</h3>
              <p>
                Extract important information using OCR and AI.
              </p>
            </div>

            <div className="feature">
              <div className="feature-icon">💬</div>
              <h3>Ask Questions</h3>
              <p>
                Ask multiple questions and get simple explanations.
              </p>
            </div>
          </section>
        )}
      </main>

      <footer>
        <p>© 2026 MediMind AI • Built with AI & RAG</p>
      </footer>
    </div>
  );
}

export default App;