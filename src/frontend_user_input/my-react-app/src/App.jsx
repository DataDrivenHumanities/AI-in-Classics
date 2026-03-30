import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'


function App() {
  const [count, setCount] = useState(0)
  const [text, setText] = useState("")
  const [result, setResult] = useState("")
  const [model, setModel] = useState("BERT Model")


  function handleLemmatize() {
    setResult(`${"Positive"}`)
  }


  return (
    <>
    <div className="flex flex-col items-center justify-center min-h-screen bg-blue-900">
      <div className="text-5xl mb-10 text-white">
        <h1>Lemmatizer for User Input</h1>
      </div>


      <div className="mb-4 w-96 text-white">
        <select
          className="w-full p-2 rounded bg-blue-900 text-white border border-white"
          value={model}
          onChange={(e) => setModel(e.target.value)}
        >
          <option>BERT Model </option>
          <option>GPT Model</option>
        </select>
      </div>


      <div className="border-2 border-gray-400 rounded-lg p-4 w-150">
        <textarea
          className="w-full h-75 p-2 border rounded resize-none text-white"
          placeholder="Enter text here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </div>


      <button
        onClick={handleLemmatize}
        className="mt-4 px-6 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
      >
        Lemmatize
      </button>


      <div className="mt-6 w-96 border p-3 rounded text-white">
        <strong>Result:</strong> {result}
      </div>


      </div>
    </>
  )
}


export default App