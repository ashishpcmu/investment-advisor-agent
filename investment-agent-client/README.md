# Investment Strategy Agent React App

A modern React application that provides an interactive UI for generating personalized investment strategies based on user goals and preferences.

## Features

- Interactive investment goal input with natural language processing
- Customizable risk tolerance, investment horizon, and portfolio size settings
- Real-time visualization of investment recommendations using Recharts
- Feedback mechanism to refine and improve investment strategies
- Responsive design for desktop and mobile devices

## Screenshots

![Investment Strategy Agent](/screenshots/investment-strategy-agent.png)

## Tech Stack

- React (with Hooks)
- Recharts for data visualization
- Tailwind CSS for styling
- Fetch API for backend communication

## Prerequisites

- Node.js (v14.0.0 or higher)
- npm (v6.0.0 or higher) or yarn
- Connection to the Investment Strategy Advisor API (FastAPI backend)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd investment-strategy-agent
```

2. Install dependencies:

```bash
npm install
# or
yarn
```

3. Configure API endpoint:

Open `src/components/InvestmentStrategyAgent.jsx` and update the API_URL constant to point to your backend API:

```javascript
// Change this to match your FastAPI server address
const API_URL = 'http://localhost:8000';
```

## Running the Application

Start the development server:

```bash
npm run dev
# or
yarn dev
```

The application will be available at `http://localhost:5173` (or another port if 5173 is in use).

## Building for Production

To create a production build:

```bash
npm run build
# or
yarn build
```

The build files will be generated in the `dist` directory, which you can then deploy to a web server.

## Project Structure

- `src/components/InvestmentStrategyAgent.jsx` - Main component implementing the investment strategy UI
- `src/components/InvestmentStrategyAgent.css` - Component-specific styles

## Key Component Features

### Settings Panel

The settings panel allows users to customize:

- Risk tolerance (Low, Medium, High)
- Investment horizon (1-30 years)
- Portfolio size ($1,000 - $1,000,000)

### Chat Interface

The app uses a chat-like interface where:

1. Users submit their investment goals
2. The system processes and returns a detailed investment strategy
3. Users can provide feedback on the strategy
4. The system can revise the strategy based on feedback

### Investment Strategy Visualization

The returned investment strategy includes:

- Asset allocation breakdown with color-coded bar chart
- Detailed product recommendations
- Interactive pie chart for portfolio visualization
- Agent insights with risk scores and confidence metrics
- Estimated portfolio growth projections

## API Integration

The app integrates with the FastAPI backend through two main endpoints:

- `POST /api/generate-strategy` - Generates an investment strategy based on user input
- `POST /api/process-feedback` - Processes user feedback and improves recommendations

## Troubleshooting

If you encounter issues connecting to the API:

1. Ensure the FastAPI server is running
2. Check that the API_URL is correctly set
3. Verify that CORS is properly configured on the backend
4. Check browser console for detailed error messages

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT License](LICENSE)