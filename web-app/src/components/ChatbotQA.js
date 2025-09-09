import React, { useState } from 'react';
import './ChatbotQA.css';

const API_BASE = "https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod";

const ChatbotQA = ({ documentData }) => {
  const [messages, setMessages] = useState([{
    type: 'ai',
    text: 'Hello! I can help you understand your tax documents. Ask me about wages, taxes, employer information, or any other details from your processed forms.'
  }]);
  const [input, setInput] = useState('');
  const [docs, setDocs] = useState([]);

  const getUserId = () => {
    let id = localStorage.getItem('taxdoc_user');
    if (!id) { id = 'ANON'; localStorage.setItem('taxdoc_user', id); }
    return id;
  };

  const loadDocs = async () => {
    try {
      const userId = getUserId();
      const r = await fetch(`${API_BASE}/documents?userId=${encodeURIComponent(userId)}`);
      if (!r.ok) throw new Error(`documents failed: ${r.status}`);
      const { items = [] } = await r.json();
      const processed = items.filter(d => (d.status || "PROCESSED") === "PROCESSED");
      setDocs(processed);
      return processed;
    } catch (e) {
      console.error('Failed to load docs:', e);
      return [];
    }
  };

  const flattenFields = (fields = {}) => {
    const out = {};
    for (const [k, v] of Object.entries(fields)) {
      const val = typeof v === "object" && "value" in v ? v.value : v;
      if (val != null && String(val).trim() !== "") out[k] = String(val);
    }
    return out;
  };

  const maskSSN = (s) => s.replace(/^(\d{3})-(\d{2})-(\d{4})$/, '***-**-$3');

  const answerEmployerInfo = async () => {
    const docs = await loadDocs();
    const w2 = docs.filter(d => d.docType?.toLowerCase() === "w-2" || d.docType === "w2")
                   .sort((a, b) => (b.processedAt || 0) - (a.processedAt || 0))[0];
    
    if (!w2) return "I don't see a processed W-2 yet. Please process one and try again.";

    const f = flattenFields(w2.fields);
    const name = f['Employer Name'] || f.employer_name || "Unknown employer";
    const ein = f['Employer EIN'] || f.employer_ein || "Unknown EIN";
    
    let msg = `Employer Name: ${name}\nEmployer EIN: ${ein}`;
    return msg;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { type: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    
    let response;
    if (input.toLowerCase().includes('employer')) {
      response = await answerEmployerInfo();
    } else {
      response = await generateResponse(input);
    }
    
    const aiResponse = { type: 'ai', text: response };
    setMessages(prev => [...prev, aiResponse]);
    setInput('');
  };

  const generateResponse = async (query) => {
    const docs = await loadDocs();
    if (!docs || docs.length === 0) {
      return "I don't see any processed documents. Please upload and process a document first.";
    }

    const queryLower = query.toLowerCase();
    const responses = [];

    docs.forEach(doc => {
      const f = flattenFields(doc.fields);
      
      if (queryLower.includes('wage') || queryLower.includes('income')) {
        const wages = f['Box 1 - Wages'] || f.box1_wages;
        if (wages) {
          responses.push(`**${doc.filename}**: Wages/Income: ${wages}`);
        }
      }
      
      if (queryLower.includes('tax')) {
        const fedTax = f['Box 2 - Federal Tax'] || f.box2_fed_tax;
        const ssTax = f['Box 4 - SS Tax'] || f.box4_ss_tax;
        const medicareTax = f['Box 6 - Medicare Tax'] || f.box6_medicare_tax;
        
        if (fedTax || ssTax || medicareTax) {
          let taxInfo = `**${doc.filename}** taxes:\n`;
          if (fedTax) taxInfo += `• Federal: ${fedTax}\n`;
          if (ssTax) taxInfo += `• Social Security: ${ssTax}\n`;
          if (medicareTax) taxInfo += `• Medicare: ${medicareTax}`;
          responses.push(taxInfo);
        }
      }
    });

    return responses.length > 0 ? responses.join('\n\n') : 
      `I found ${docs.length} processed document(s), but couldn't find specific information about "${query}". Try asking about wages, taxes, employer details, or other specific fields.`;
  };

  React.useEffect(() => {
    loadDocs();
  }, []);

  // Remove documentData dependency - we fetch directly

  return (
    <div className="chatbot-qa">
      <div className="chatbot-header">
        <h3>💬 AI Document Chatbot</h3>
        <p>Ask questions about your processed documents</p>
      </div>
      
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type}`}>
            <div className="message-content">
              {msg.text.split('\n').map((line, i) => (
                <div key={i}>{line.startsWith('**') ? <strong>{line.replace(/\*\*/g, '')}</strong> : line}</div>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <form onSubmit={handleSubmit} className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about wages, taxes, employer info..."
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
};

export default ChatbotQA;