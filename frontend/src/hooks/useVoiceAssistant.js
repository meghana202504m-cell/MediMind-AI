import { useEffect, useRef, useState } from "react";

const VOICE_LOCALES = {
  en: "en-US",
  kn: "kn-IN",
  hi: "hi-IN",
};

function findVoice(language) {
  if (typeof window === "undefined" || !window.speechSynthesis) return null;
  const locale = VOICE_LOCALES[language];
  const voices = window.speechSynthesis.getVoices();
  return voices.find((voice) => voice.lang.toLowerCase() === locale.toLowerCase()) ||
    voices.find((voice) => voice.lang.toLowerCase().startsWith(locale.slice(0, 2))) ||
    null;
}

export function useVoiceAssistant(language, onTranscript) {
  const recognitionRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [voiceMessage, setVoiceMessage] = useState("");
  const supported = typeof window !== "undefined" && Boolean(
    window.SpeechRecognition || window.webkitSpeechRecognition,
  );
  const speechSupported = typeof window !== "undefined" && Boolean(window.speechSynthesis);

  useEffect(() => () => {
    recognitionRef.current?.stop();
    window.speechSynthesis?.cancel();
  }, []);

  const startListening = () => {
    if (!supported || listening) return;
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new Recognition();
    recognition.lang = VOICE_LOCALES[language] || VOICE_LOCALES.en;
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onstart = () => {
      setListening(true);
      setVoiceMessage("");
    };
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim();
      if (transcript) onTranscript(transcript);
    };
    recognition.onerror = (event) => {
      setVoiceMessage(event.error === "not-allowed"
        ? "Microphone access was denied. Allow microphone access and try again."
        : "Voice input is unavailable right now. You can type your question instead.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopListening = () => {
    recognitionRef.current?.stop();
    setListening(false);
  };

  const speak = (text) => {
    if (!speechSupported) {
      setVoiceMessage("Text-to-speech is not supported in this browser.");
      return;
    }
    const voice = findVoice(language);
    if (!voice && language !== "en") {
      setVoiceMessage("A voice for the selected language is not available on this device.");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = VOICE_LOCALES[language] || VOICE_LOCALES.en;
    utterance.voice = voice || null;
    utterance.onstart = () => {
      setSpeaking(true);
      setVoiceMessage("");
    };
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => {
      setSpeaking(false);
      setVoiceMessage("Text-to-speech could not play this response.");
    };
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  };

  return {
    listening,
    speaking,
    supported,
    speechSupported,
    voiceMessage,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  };
}
