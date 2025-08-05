import React, { useState } from 'react';
import './ChatbotQA.css';

const ChatbotQA = ({ documentData }) => {
  if (!documentData) return null;

  
  return (
    <div className="chatbot-qa">
      <div className="chatbot-header">
        <h3>💬 Document Q&A</h3>
      </div>
      <p>Q&A functionality will be available when AI insights are implemented.</p>
    </div>
  );
};

export default ChatbotQA;