import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import InvestmentStrategyAgent from './InvestmentStrategyAgent'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <InvestmentStrategyAgent />
    </>
  )
}

export default App