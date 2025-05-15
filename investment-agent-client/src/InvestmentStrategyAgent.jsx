import { useState, useEffect, useRef } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

const InvestmentStrategyAgent = () => {
  // State for user input
  const [goalText, setGoalText] = useState('');
  const [riskTolerance, setRiskTolerance] = useState(2);
  const [investmentHorizon, setInvestmentHorizon] = useState(10);
  const [portfolioSize, setPortfolioSize] = useState(10000);
  const [messages, setMessages] = useState([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(true); // Show settings by default
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Check if we need to wait for feedback
  const [waitingForFeedback, setWaitingForFeedback] = useState(false);
  const [currentRecommendationId, setCurrentRecommendationId] = useState(null);
  const [hasSubmittedOnce, setHasSubmittedOnce] = useState(false);
  
  // Ref for scrolling to response
  const latestResponseRef = useRef(null);
  
  // API URL (change in production)
  //const API_URL = 'http://localhost:8000';
  const API_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

  
  // Conversion functions
  const convertRiskToleranceToText = (value) => {
    if (value === 1) return 'low';
    if (value === 2) return 'medium';
    return 'high';
  };
  
  const convertHorizonToText = (years) => {
    if (years < 10) return 'short-term';
    if (years <= 20) return 'medium-term';
    return 'long-term';
  };
  
  // Function to generate investment recommendation via API
  const generateRecommendation = async () => {
    if (!goalText.trim()) return;
    
    setIsLoading(true);
    setError(null);
    
    // If this is the first submission, auto-close settings panel
    if (!hasSubmittedOnce) {
      setHasSubmittedOnce(true);
      setIsSettingsOpen(false);
    }
    
    // If we're waiting for feedback, treat this as feedback submission
    if (waitingForFeedback && currentRecommendationId) {
      await submitFeedback(goalText, currentRecommendationId);
      return;
    }
    
    // Add user message to chat
    setMessages(prev => [...prev, {
      type: 'user',
      content: goalText
    }]);
    
    try {
      // Create data for API request
      const requestData = {
        goal_text: goalText,
        risk_tolerance: riskTolerance,
        investment_horizon: investmentHorizon,
        portfolio_size: portfolioSize
      };
      
      // Make API request to backend
      const response = await fetch(`${API_URL}/api/generate-strategy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
      
      const result = await response.json();
      
      // Add system response
      setMessages(prev => [...prev, {
        type: 'system',
        content: {
          recommendation_id: result.recommendation_id,
          goal: goalText,
          structured_goal: result.structured_goal,
          recommendation: result.strategy,
          agents: result.agent_insights,
          presentation: result.presentation
        }
      }]);
      
      // Set waiting for feedback and store recommendation ID
      setWaitingForFeedback(true);
      setCurrentRecommendationId(result.recommendation_id);
      
      // Add feedback prompt message
      setMessages(prev => [...prev, {
        type: 'prompt',
        content: "How does this recommendation look? If you're satisfied, please type 'I'm satisfied'. Otherwise, please explain what changes you'd like to see."
      }]);
      
      // Clear input
      setGoalText('');
      
    } catch (err) {
      // Show error message
      setError(`Failed to generate recommendation: ${err.message}`);
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Failed to generate recommendation. Please try again.`
      }]);
      
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    generateRecommendation();
  };
  
  const submitFeedback = async (feedbackText, recommendationId) => {
    if (!feedbackText.trim()) return;
    
    // Add user feedback to chat
    setMessages(prev => [...prev, {
      type: 'user',
      content: feedbackText
    }]);
    
    // Check if user is satisfied
    if (feedbackText.toLowerCase().includes("satisfied") || 
        feedbackText.toLowerCase().includes("good") || 
        feedbackText.toLowerCase().includes("great") ||
        feedbackText.toLowerCase().includes("perfect")) {
      
      // Add completion message
      setMessages(prev => [...prev, {
        type: 'system',
        content: {
          presentation: "Excellent! I'm glad you're satisfied with the recommendation. Your investment strategy is now ready to implement. If you have any questions in the future or want to adjust your strategy, just let me know."
        }
      }]);
      
      // Reset feedback state
      setWaitingForFeedback(false);
      setCurrentRecommendationId(null);
      setGoalText('');
      return;
    }
    
    setIsLoading(true);
    
    try {
      // Create data for API request
      const requestData = {
        recommendation_id: recommendationId,
        feedback_text: feedbackText
      };
      
      // Make API request to backend
      const response = await fetch(`${API_URL}/api/process-feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
      
      const result = await response.json();
      
      // Store feedback in previous recommendation message
      const recommendationMessageIndex = messages.findIndex(
        msg => msg.type === 'system' && msg.content.recommendation_id === recommendationId
      );
      
      if (recommendationMessageIndex >= 0) {
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[recommendationMessageIndex] = {
            ...newMessages[recommendationMessageIndex],
            feedback: feedbackText,
            feedback_analysis: result
          };
          return newMessages;
        });
      }
      
      // Make another API request to generate a revised strategy
      const revisedRequestData = {
        goal_text: `Based on my previous recommendation and this feedback: "${feedbackText}", please revise the investment strategy. ${result.risk_adjustment !== "no change" ? `Adjust risk to be ${result.risk_adjustment}.` : ''}`,
        risk_tolerance: result.risk_adjustment === "higher" ? Math.min(riskTolerance + 1, 3) : 
                       result.risk_adjustment === "lower" ? Math.max(riskTolerance - 1, 1) : riskTolerance,
        investment_horizon: investmentHorizon,
        portfolio_size: portfolioSize
      };
      
      // Make API request for revised strategy
      const revisedResponse = await fetch(`${API_URL}/api/generate-strategy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(revisedRequestData)
      });
      
      if (!revisedResponse.ok) {
        throw new Error(`Error: ${revisedResponse.status}`);
      }
      
      const revisedResult = await revisedResponse.json();
      
      // Add revised system response
      setMessages(prev => [...prev, {
        type: 'system',
        content: {
          recommendation_id: revisedResult.recommendation_id,
          goal: revisedRequestData.goal_text,
          structured_goal: revisedResult.structured_goal,
          recommendation: revisedResult.strategy,
          agents: revisedResult.agent_insights,
          presentation: revisedResult.presentation
        }
      }]);
      
      // Update current recommendation ID to the new one
      setCurrentRecommendationId(revisedResult.recommendation_id);
      
      // Add feedback prompt message
      setMessages(prev => [...prev, {
        type: 'prompt',
        content: "How does this revised recommendation look? If you're satisfied, please type 'I'm satisfied'. Otherwise, please explain what further changes you'd like to see."
      }]);
      
      // Clear input
      setGoalText('');
      
    } catch (err) {
      // Show error message
      setError(`Failed to process feedback: ${err.message}`);
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Failed to update recommendation. Please try again.`
      }]);
      
      // Reset feedback state
      setWaitingForFeedback(false);
      setCurrentRecommendationId(null);
      
    } finally {
      setIsLoading(false);
    }
  };
  
  // Scroll to bottom of messages when they change
  useEffect(() => {
    const messagesContainer = document.querySelector('.messages-container');
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }, [messages]);
  
  // Scroll to the latest system response when it's added
  useEffect(() => {
    if (latestResponseRef.current) {
      latestResponseRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [messages]);
  
  // Create a modified dataset for the pie chart that ensures proper display of percentages
  const createPieChartData = (products) => {
    if (!products || !Array.isArray(products)) return [];
    
    // Extract just the necessary data for the pie chart and ensure percentages are numeric
    return products.map(product => {
      const name = product.name.split(' ')[0]; // Get just the first word/ticker
      const percentage = typeof product.percentage === 'string' 
        ? parseFloat(product.percentage.replace('%', '')) 
        : product.percentage;
        
      return {
        name,
        percentage,
        fullName: product.name,
        description: product.description
      };
    });
  };
  
  // Render a system message (recommendation)
  const renderSystemMessage = (message, index) => {
    const isLatestSystemMessage = messages
      .filter(m => m.type === 'system')
      .indexOf(message) === messages.filter(m => m.type === 'system').length - 1;
    
    if (!message.content) return null;
    
    const { structured_goal, recommendation, agents, presentation } = message.content;
    
    if (!structured_goal && !recommendation && !agents && presentation) {
      // Simple presentation message (e.g., final confirmation)
      return (
        <div 
          className="bg-white rounded-lg shadow-md p-4 mb-4 max-w-3xl mx-auto"
          ref={isLatestSystemMessage ? latestResponseRef : null}
        >
          <p className="text-gray-700">{presentation}</p>
        </div>
      );
    }
    
    // Create pie chart data
    const pieChartData = recommendation && recommendation.products 
      ? createPieChartData(recommendation.products) 
      : [];
    
    return (
      <div 
        className="bg-white rounded-lg shadow-md p-4 mb-4 max-w-3xl mx-auto"
        ref={isLatestSystemMessage ? latestResponseRef : null}
      >
        <div className="bg-green-50 p-4 rounded-md mb-4">
          <p className="font-medium">Your Goal:</p>
          <p className="text-gray-700">{message.content.goal}</p>
        </div>
        
        {structured_goal && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="font-medium text-gray-700">Goal Type:</p>
              <p className="text-lg font-bold text-green-800 capitalize">{structured_goal.goal_type}</p>
            </div>
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="font-medium text-gray-700">Time Horizon:</p>
              <p className="text-lg font-bold text-green-800 capitalize">{structured_goal.investment_horizon}</p>
            </div>
            <div className="bg-gray-50 p-3 rounded-md">
              <p className="font-medium text-gray-700">Risk Tolerance:</p>
              <p className="text-lg font-bold text-green-800 capitalize">{structured_goal.risk_tolerance}</p>
            </div>
          </div>
        )}
        
        {recommendation && recommendation.allocation && (
          <div className="mb-4">
            <h3 className="font-bold text-lg mb-2">Recommended Allocation</h3>
            <div className="h-6 w-full flex rounded-md overflow-hidden">
              {Object.entries(recommendation.allocation).map(([asset, percentage], i) => (
                <div 
                  key={asset}
                  className={`h-full ${i % 3 === 0 ? 'bg-green-200' : i % 3 === 1 ? 'bg-green-500' : 'bg-green-700'}`}
                  style={{width: `${percentage}%`}}
                  title={`${asset}: ${percentage}%`}
                />
              ))}
            </div>
            <div className="flex flex-wrap mt-2 text-sm text-gray-600 gap-x-4">
              {Object.entries(recommendation.allocation).map(([asset, percentage], i) => (
                <span key={asset} className="flex items-center">
                  <span className={`w-3 h-3 ${i % 3 === 0 ? 'bg-green-200' : i % 3 === 1 ? 'bg-green-500' : 'bg-green-700'} mr-1 inline-block`}></span>
                  {asset}: {percentage}%
                </span>
              ))}
            </div>
          </div>
        )}
        
        {recommendation && recommendation.products && (
          <div className="mb-4">
            <h3 className="font-bold text-lg mb-2">Recommended Products</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {recommendation.products.map((product, i) => (
                <div key={i} className="border rounded-md p-3">
                  <p className="font-medium">{product.name} ({product.percentage}%)</p>
                  <p className="text-sm text-gray-600">{product.description}</p>
                </div>
              ))}
            </div>
            
            {/* Products Pie Chart - Enlarged with more padding */}
            {pieChartData.length > 0 && (
              <div className="my-12 h-80">
                <h4 className="text-center text-gray-700 mb-4">Asset Allocation</h4>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={120}
                      fill="#8884d8"
                      dataKey="percentage"
                      nameKey="name"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      fontSize={12}
                    >
                      {pieChartData.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={`hsl(${120 + index * 40}, ${50 + index * 5}%, ${40 + index * 5}%)`} 
                        />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value) => `${value}%`}
                      labelFormatter={(_, payload) => payload[0]?.payload?.fullName || ''}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
        
        {agents && (
          <div className="my-8 py-4">
            <h3 className="font-bold text-lg mb-2">Agent Insights</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border rounded-md p-3">
                <p className="text-sm text-gray-500">Risk Agent</p>
                <p className="font-medium">Risk Score: {agents.risk_agent_score}/10</p>
              </div>
              <div className="border rounded-md p-3">
                <p className="text-sm text-gray-500">Goal Agent</p>
                <p className="font-medium">Confidence: {agents.goal_agent_confidence * 100}%</p>
              </div>
              <div className="border rounded-md p-3">
                <p className="text-sm text-gray-500">Investment Agent</p>
                <p className="font-medium">Predicted Return: {agents.investment_agent_prediction}</p>
              </div>
            </div>
            
            {/* Estimated Portfolio Value */}
            <div className="mt-4 bg-green-50 p-4 rounded-md">
              <h4 className="font-bold mb-2">Estimated Portfolio Growth</h4>
              {(() => {
                // Parse the predicted return from the string (e.g., "7% annual return")
                const predictedReturnMatch = agents.investment_agent_prediction.match(/(\d+)/);
                const predictedReturn = predictedReturnMatch ? parseFloat(predictedReturnMatch[0]) / 100 : 0.05;
                
                // Get the initial investment amount
                const initialInvestment = message.content.recommendation_id ? 
                  parseInt(message.content.goal.match(/portfolio size is \$(\d+)/i)?.[1] || portfolioSize) : 
                  portfolioSize;
                
                // Get the time horizon
                const timeHorizon = message.content.recommendation_id ?
                  parseInt(message.content.goal.match(/investment horizon is (\d+)/i)?.[1] || (structured_goal.investment_horizon === "short-term" ? 5 : structured_goal.investment_horizon === "medium-term" ? 15 : 25)) :
                  (structured_goal.investment_horizon === "short-term" ? 5 : structured_goal.investment_horizon === "medium-term" ? 15 : 25);
                
                // Calculate estimated future value
                const estimatedValue = initialInvestment * Math.pow(1 + predictedReturn, timeHorizon);
                
                return (
                  <div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-white rounded-md p-3 shadow-sm">
                        <p className="text-sm text-gray-500">Initial Investment</p>
                        <p className="text-xl font-bold text-green-800">${initialInvestment.toLocaleString()}</p>
                      </div>
                      <div className="bg-white rounded-md p-3 shadow-sm">
                        <p className="text-sm text-gray-500">Time Horizon</p>
                        <p className="text-xl font-bold text-green-800">{timeHorizon} years</p>
                      </div>
                    </div>
                    <div className="mt-4 bg-green-100 rounded-md p-4 shadow-sm text-center">
                      <p className="text-sm text-gray-500">Estimated Future Value</p>
                      <p className="text-2xl font-bold text-green-800">${Math.round(estimatedValue).toLocaleString()}</p>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        )}
        
        {recommendation && recommendation.rationale && (
          <div className="mb-4">
            <h3 className="font-bold text-lg mb-2">Strategy Rationale</h3>
            <p className="text-gray-700">{recommendation.rationale}</p>
          </div>
        )}
        
        {!message.feedback && (
          <div className="mt-4 bg-green-50 p-3 rounded-md">
            <h3 className="font-bold text-lg mb-2">How satisfied are you with this recommendation?</h3>
            <p className="text-gray-700">
              Please provide your feedback in the message box below. 
              <span className="font-medium"> If this meets your needs, simply type "I'm satisfied" or if you would like adjustments, 
              explain what you'd like changed (e.g., "Too risky", "Need more diversification", etc.)</span>
            </p>
          </div>
        )}
        
        {message.feedback && (
          <div className="mt-4 bg-gray-50 p-3 rounded-md">
            <p className="font-medium text-gray-700">Your Feedback:</p>
            <p className="text-gray-700">{message.feedback}</p>
            
            {message.feedback_analysis && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <p className="font-medium text-gray-700">Analysis:</p>
                <p className="text-gray-700">{message.feedback_analysis.feedback_analysis}</p>
                
                {message.feedback_analysis.risk_adjustment !== "no change" && (
                  <p className="text-gray-700 mt-1">
                    <span className="font-medium">Risk adjustment:</span> {message.feedback_analysis.risk_adjustment}
                  </p>
                )}
                
                {message.feedback_analysis.preference_changes && message.feedback_analysis.preference_changes.length > 0 && (
                  <p className="text-gray-700 mt-1">
                    <span className="font-medium">Preference changes:</span> {message.feedback_analysis.preference_changes.join(", ")}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };
  
  // Render a user message
  const renderUserMessage = (message) => {
    return (
      <div className="bg-green-50 rounded-lg p-3 mb-4 max-w-3xl ml-auto mr-4">
        <p className="text-gray-800">{message.content}</p>
      </div>
    );
  };
  
  // Render an error message
  const renderError = (message) => {
    return (
      <div className="bg-red-50 text-red-800 rounded-lg p-3 mb-4 max-w-3xl mx-auto">
        <p>{message.content}</p>
      </div>
    );
  };
  
  // Render a prompt message
  const renderPromptMessage = (message) => {
    return (
      <div className="bg-green-50 border border-green-200 text-green-800 rounded-lg p-3 mb-4 max-w-3xl mx-auto">
        <p>{message.content}</p>
      </div>
    );
  };
  
  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="py-4 px-6 bg-white border-b border-gray-200 shadow-sm">
        <h1 className="text-xl font-bold text-green-800">Investment Strategy Agent</h1>
      </header>
      
      {/* Loading indicator overlay */}
      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg flex flex-col items-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-500 mb-4"></div>
            <p className="text-gray-700 font-medium">Processing the Agent's Response...</p>
          </div>
        </div>
      )}
      
      {/* Messages area - scrollable */}
      <div className="flex-1 overflow-y-auto p-4 pb-32 messages-container">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="bg-white rounded-lg shadow-md p-6 max-w-md">
              <h2 className="text-2xl font-bold text-green-800 mb-4">Welcome to Investment Strategy Agent</h2>
              <p className="text-gray-600 mb-4">
                Get personalized investment recommendations based on your financial goals and preferences.
              </p>
              <p className="text-gray-600">
                Enter your investment goals below to get started.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div key={index}>
                {message.type === 'user' && renderUserMessage(message)}
                {message.type === 'system' && renderSystemMessage(message, index)}
                {message.type === 'error' && renderError(message)}
                {message.type === 'prompt' && renderPromptMessage(message)}
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Input area - fixed at bottom */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-md p-4">
        <div className="max-w-4xl mx-auto">
          {isSettingsOpen && (
            <div className="mb-4 bg-gray-100 p-3 rounded-lg">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-gray-700 font-medium mb-2">
                    Risk Tolerance: {convertRiskToleranceToText(riskTolerance) === 'low' ? 'Low' : convertRiskToleranceToText(riskTolerance) === 'medium' ? 'Medium' : 'High'}
                  </label>
                  <input 
                    type="range" 
                    min="1" 
                    max="3" 
                    value={riskTolerance}
                    onChange={(e) => setRiskTolerance(parseInt(e.target.value))}
                    className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: 'linear-gradient(to right, #d1fae5, #34d399, #059669)',
                      height: '8px'
                    }}
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Low</span>
                    <span>Medium</span>
                    <span>High</span>
                  </div>
                </div>
                
                <div>
                  <label className="block text-gray-700 font-medium mb-2">
                    Investment Horizon: {investmentHorizon} years
                  </label>
                  <input 
                    type="range" 
                    min="1" 
                    max="30" 
                    value={investmentHorizon}
                    onChange={(e) => setInvestmentHorizon(parseInt(e.target.value))}
                    className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: 'linear-gradient(to right, #d1fae5, #34d399, #059669)',
                      height: '8px'
                    }}
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Short-term</span>
                    <span>Medium-term</span>
                    <span>Long-term</span>
                  </div>
                </div>
                
                <div>
                  <label className="block text-gray-700 font-medium mb-2">
                    Portfolio Size: ${portfolioSize.toLocaleString()}
                  </label>
                  <input 
                    type="range" 
                    min="1000" 
                    max="1000000" 
                    step="1000"
                    value={portfolioSize}
                    onChange={(e) => setPortfolioSize(parseInt(e.target.value))}
                    className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: 'linear-gradient(to right, #d1fae5, #34d399, #059669)',
                      height: '8px'
                    }}
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>$1,000</span>
                    <span>$500,000</span>
                    <span>$1,000,000</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="flex items-center">
            <button 
              type="button"
              onClick={() => setIsSettingsOpen(!isSettingsOpen)}
              className={`mr-2 p-2 ${isSettingsOpen ? 'text-green-600' : 'text-gray-500'} hover:text-green-600 focus:outline-none`}
              title="Toggle investment preferences"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
            
            <input
              type="text"
              placeholder={waitingForFeedback ? "Provide feedback on this recommendation..." : "Describe your investment goals (e.g., I want to invest for retirement with low risk)"}
              className="flex-1 p-3 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-green-500"
              value={goalText}
              onChange={(e) => setGoalText(e.target.value)}
              required
              disabled={isLoading}
            />
            
            <button 
              type="submit"
              className={`p-3 bg-green-600 text-white font-medium rounded-r-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              disabled={isLoading}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default InvestmentStrategyAgent;
