import React, { useState } from 'react';
import './ChatbotQA.css';

const ChatbotQA = ({ documentData }) => {
  const [messages, setMessages] = useState([{
    type: 'ai',
    text: 'Hello! I can help you understand your tax documents. Ask me about wages, taxes, employer information, or any other details from your processed forms.'
  }]);
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { type: 'user', text: input };
    const aiResponse = { type: 'ai', text: generateResponse(input, documentData) };
    
    setMessages(prev => [...prev, userMessage, aiResponse]);
    setInput('');
  };

  const generateResponse = (query, docs) => {
    if (!docs || docs.length === 0) {
      return "I don't see any processed documents. Please upload and process a document first.";
    }

    const queryLower = query.toLowerCase();
    const responses = [];

    docs.forEach(doc => {
      if (queryLower.includes('employer')) {
        const employerName = doc.fields?.['Employer Name'] || doc.fields?.['employer_name'];
        const employerEIN = doc.fields?.['Employer EIN'] || doc.fields?.['employer_ein'];
        
        if (employerName || employerEIN) {
          responses.push(`**${doc.filename}** (${doc.docType}):\n${employerName ? `• Employer: ${employerName}` : ''}${employerEIN ? `\n• EIN: ${employerEIN}` : ''}`);
        }
      }
      
      if (queryLower.includes('wage') || queryLower.includes('income')) {
        const wages = doc.fields?.['Box 1 - Wages'] || doc.fields?.['box1_wages'];
        if (wages) {
          responses.push(`**${doc.filename}**: Wages/Income: ${wages}`);
        }
      }
      
      if (queryLower.includes('tax')) {
        const fedTax = doc.fields?.['Box 2 - Federal Tax'] || doc.fields?.['box2_fed_tax'];
        const ssTax = doc.fields?.['Box 4 - SS Tax'] || doc.fields?.['box4_ss_tax'];
        const medicareTax = doc.fields?.['Box 6 - Medicare Tax'] || doc.fields?.['box6_medicare_tax'];
        
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

  if (!documentData) return null;

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