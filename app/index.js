import { useState } from 'react';

const InvestmentStrategyAgent = () => {
  // State for user input
  const [goalText, setGoalText] = useState('');
  const [riskTolerance, setRiskTolerance] = useState(2);
  const [investmentHorizon, setInvestmentHorizon] = useState(10);
  const [portfolioSize, setPortfolioSize] = useState(10000);
  const [submitted, setSubmitted] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const [feedback, setFeedback] = useState('');
  
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
  
  // Mock recommendation generation
  const generateRecommendation = () => {
    // This would normally call the backend with all the agent processing
    // For now, we're using a mock response
    const riskText = convertRiskToleranceToText(riskTolerance);
    const horizonText = convertHorizonToText(investmentHorizon);
    
    const mockRecommendation = {
      goal: goalText,
      structured_goal: {
        goal_type: goalText.toLowerCase().includes('retire') ? 'retirement' : 
                   goalText.toLowerCase().includes('education') ? 'education' : 'general',
        investment_horizon: horizonText,
        risk_tolerance: riskText,
        investment_preferences: ["ETF", "robo-advisor"]
      },
      recommendation: {
        strategy: riskText === 'low' ? 
          { bonds: 70, etf: 30 } : 
          riskText === 'medium' ? 
            { bonds: 50, etf: 30, stocks: 20 } : 
            { bonds: 20, etf: 40, stocks: 40 }
      },
      agents: {
        risk_agent_score: riskTolerance * 3,
        goal_agent_confidence: 0.85,
        investment_agent_prediction: `${5 + riskTolerance}% annual return`
      }
    };
    
    setRecommendation(mockRecommendation);
    setSubmitted(true);
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    generateRecommendation();
  };
  
  const submitFeedback = () => {
    // This would normally call the FeedbackAgent
    alert('Feedback submitted: ' + feedback);
    setFeedback('');
  };
  
  const resetForm = () => {
    setSubmitted(false);
    setRecommendation(null);
    setGoalText('');
  };
  
  return (
    <div className="flex flex-col min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto w-full">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-green-800">Investment Strategy Agent</h1>
          <p className="text-gray-600 mt-2">Get personalized investment recommendations based on your goals and preferences</p>
        </header>
        
        {!submitted ? (
          <div className="bg-white rounded-lg shadow-md p-6">
            <form onSubmit={handleSubmit}>
              <div className="mb-6">
                <label className="block text-gray-700 font-medium mb-2">
                  Risk Tolerance: {convertRiskToleranceToText(riskTolerance) === 'low' ? 'Low' : convertRiskToleranceToText(riskTolerance) === 'medium' ? 'Medium' : 'High'}
                </label>
                <input 
                  type="range" 
                  min="1" 
                  max="3" 
                  value={riskTolerance}
                  onChange={(e) => setRiskTolerance(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Low</span>
                  <span>Medium</span>
                  <span>High</span>
                </div>
              </div>
              
              <div className="mb-6">
                <label className="block text-gray-700 font-medium mb-2">
                  Investment Horizon: {investmentHorizon} years
                </label>
                <input 
                  type="range" 
                  min="1" 
                  max="30" 
                  value={investmentHorizon}
                  onChange={(e) => setInvestmentHorizon(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Short-term</span>
                  <span>Medium-term</span>
                  <span>Long-term</span>
                </div>
              </div>
              
              <div className="mb-6">
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
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>$1,000</span>
                  <span>$500,000</span>
                  <span>$1,000,000</span>
                </div>
              </div>
              
              <div className="mb-6">
                <label className="block text-gray-700 font-medium mb-2">What are your investment goals?</label>
                <textarea 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  rows="3"
                  placeholder="Example: I want to invest for retirement with low risk, or I need to save for my child's education in 10 years"
                  value={goalText}
                  onChange={(e) => setGoalText(e.target.value)}
                  required
                />
              </div>
              
              <div className="flex justify-center">
                <button 
                  type="submit"
                  className="px-6 py-3 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  Generate Investment Strategy
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="mb-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-blue-800">Your Investment Strategy</h2>
                <button 
                  onClick={resetForm}
                  className="text-green-600 hover:text-green-800 text-sm"
                >
                  Start Over
                </button>
              </div>
              
              <div className="bg-green-50 p-4 rounded-md mb-4">
                <p className="font-medium">Your Goal:</p>
                <p className="text-gray-700">{recommendation?.goal}</p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-50 p-4 rounded-md">
                  <p className="font-medium text-gray-700">Goal Type:</p>
                  <p className="text-xl font-bold text-green-800 capitalize">{recommendation?.structured_goal.goal_type}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-md">
                  <p className="font-medium text-gray-700">Time Horizon:</p>
                  <p className="text-xl font-bold text-green-800 capitalize">{recommendation?.structured_goal.investment_horizon}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded-md">
                  <p className="font-medium text-gray-700">Risk Tolerance:</p>
                  <p className="text-xl font-bold text-green-800 capitalize">{recommendation?.structured_goal.risk_tolerance}</p>
                </div>
              </div>
              
              <div className="mb-6">
                <h3 className="font-bold text-lg mb-2">Recommended Allocation</h3>
                <div className="h-6 w-full flex rounded-md overflow-hidden">
                  {recommendation?.recommendation.strategy.bonds && (
                    <div 
                      className="bg-green-200 h-full" 
                      style={{width: `${recommendation.recommendation.strategy.bonds}%`}}
                      title={`Bonds: ${recommendation.recommendation.strategy.bonds}%`}
                    />
                  )}
                  {recommendation?.recommendation.strategy.etf && (
                    <div 
                      className="bg-green-500 h-full" 
                      style={{width: `${recommendation.recommendation.strategy.etf}%`}}
                      title={`ETFs: ${recommendation.recommendation.strategy.etf}%`}
                    />
                  )}
                  {recommendation?.recommendation.strategy.stocks && (
                    <div 
                      className="bg-green-700 h-full" 
                      style={{width: `${recommendation.recommendation.strategy.stocks}%`}}
                      title={`Stocks: ${recommendation.recommendation.strategy.stocks}%`}
                    />
                  )}
                </div>
                <div className="flex mt-2 text-sm text-gray-600 justify-between">
                  {recommendation?.recommendation.strategy.bonds && (
                    <span className="flex items-center">
                      <span className="w-3 h-3 bg-green-200 mr-1 inline-block"></span>
                      Bonds: {recommendation.recommendation.strategy.bonds}%
                    </span>
                  )}
                  {recommendation?.recommendation.strategy.etf && (
                    <span className="flex items-center">
                      <span className="w-3 h-3 bg-green-500 mr-1 inline-block"></span>
                      ETFs: {recommendation.recommendation.strategy.etf}%
                    </span>
                  )}
                  {recommendation?.recommendation.strategy.stocks && (
                    <span className="flex items-center">
                      <span className="w-3 h-3 bg-green-700 mr-1 inline-block"></span>
                      Stocks: {recommendation.recommendation.strategy.stocks}%
                    </span>
                  )}
                </div>
              </div>
              
              <div className="mb-6">
                <h3 className="font-bold text-lg mb-2">Agent Insights</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="border rounded-md p-3">
                    <p className="text-sm text-gray-500">Risk Agent</p>
                    <p className="font-medium">Risk Score: {recommendation?.agents.risk_agent_score}/10</p>
                  </div>
                  <div className="border rounded-md p-3">
                    <p className="text-sm text-gray-500">Goal Agent</p>
                    <p className="font-medium">Confidence: {recommendation?.agents.goal_agent_confidence * 100}%</p>
                  </div>
                  <div className="border rounded-md p-3">
                    <p className="text-sm text-gray-500">Investment Agent</p>
                    <p className="font-medium">Predicted Return: {recommendation?.agents.investment_agent_prediction}</p>
                  </div>
                </div>
              </div>
              
              <div className="mt-8 border-t pt-6">
                <h3 className="font-bold text-lg mb-2">How satisfied are you with this recommendation?</h3>
                <textarea 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  rows="2"
                  placeholder="Leave your feedback here (e.g., 'Too risky', 'Too conservative', etc.)"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                />
                <button 
                  onClick={submitFeedback}
                  className="mt-2 px-4 py-2 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  Submit Feedback
                </button>
              </div>
            </div>
          </div>
        )}
        
        <footer className="mt-8 text-center text-sm text-gray-500">
          <p>Investment Strategy Agent (ISA) &copy; 2025</p>
          <p className="mt-1">This is a demo application based on the PRD provided.</p>
        </footer>
      </div>
    </div>
  );
};

export default InvestmentStrategyAgent;