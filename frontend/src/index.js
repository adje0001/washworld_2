import ReactDOM from "react-dom/client";
import React, { useState } from "react";

function App() {
    
    const [message, setMessage] = useState("");
    const fetchData = async () => {
        try {
            const res = await fetch("https://fulldemo.eu.pythonanywhere.com");
            const data = await res.json();
            setMessage(data.message);
        } catch (err) {
            console.error(err);
            setMessage("Error connecting to backend");
        }
    };


    const [people, setPeople] = useState([]);
    const fetchPeople = async () => {
        try {
            const res = await fetch("https://fulldemo.eu.pythonanywhere.com/people");
            const data = await res.json();
            setPeople(data.people);
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div style={{ padding: "20px" }}>
            <h1>Washworld</h1>

            <button onClick={fetchData}>
                Get data from Flask
            </button>

            <p>{message}</p>

            <button onClick={fetchPeople}>
                Load people
            </button>

            <ul>
                {people.map((person, index) => (
                <li key={index}>{person.first_name} {person.last_name} {person.cpr}</li>
                ))}
            </ul>

        </div>
    );
}


const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);


export default App;