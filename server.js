import express from "express";
import cors from "cors";
import bodyParser from "body-parser";
import multer from "multer";
import fs from "fs";
import fetch from "node-fetch";
import momement from "moment"
import { engine } from 'express-handlebars';

const app = express();
app.use(cors());
app.use(bodyParser.json());
app.engine('handlebars', engine({}));
app.set('view engine', 'handlebars');
app.set('views', './views');


//app.use(express.static("public")); // Serve frontend


// Homepage Path
app.get('/', (req, res) => {
    res.render('home', { 
    });
});

app.get('/admin', (req, res) => {
    res.render('admin', { 
    });
});

// Configure multer for file upload
const upload = multer({ dest: "uploads/" });
let storedText = ""; // Store uploaded text for querying




const SIMILARITY_TOLERANCE = 0.55;  // 🚀 Global threshold for matches
const API_BASE_URL = "http://localhost:8080"

async function checkGuardrail(text) {
    try {
        const response = await fetch(`${API_BASE_URL}/query-embedding`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: text })
        });

        const data = await response.json();

        // 🚀 Boolean match determination based on tolerance
        const match = data.similarity_score !== null && data.similarity_score >= SIMILARITY_TOLERANCE;
        
        return {
            matched: match,
            matched_text: match ? data.matched_text : null,
            similarity_score: data.similarity_score
        };

    } catch (error) {
        console.error("Fetch error:", error);
        return {
            matched: false,
            matched_text: null,
            similarity_score: null
        };
    }
}

app.post("/api/generate", upload.single("file"), async (req, res) => {
    let queryText = req.body.prompt || ""; // User input query
    let fileContent = "";

    // 🚀 Step 1: Handle File Upload (Optional)
    if (req.file) {
        try {
            fileContent = await fs.promises.readFile(req.file.path, "utf-8");
        } catch (error) {
            console.error("Error reading file:", error);
            return res.status(500).json({ error: "Error processing file." });
        }
    }

    // 🚀 Step 2: Check Guardrails on User Input + File Content
    const fullQuery = fileContent ? `${queryText}\n\nRelevant Text:\n${fileContent}` : queryText;
    const inputGuardrailMatches = await checkGuardrail(fullQuery);

    if (inputGuardrailMatches.matched) {
        return res.json({
            warning: `⚠️ Guardrail breached in input!`,
            matched_text: inputGuardrailMatches.matched_text,
            similarity_score: inputGuardrailMatches.similarity_score
        });
    }

    try {
        // 🚀 Step 3: Query LLM
        const llmResponse = await fetch("http://localhost:11434/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model: "gemma:2b", prompt: fullQuery, stream: false }) // Streaming disabled for guardrail check
        });

        const llmResult = await llmResponse.json();
        const llmText = llmResult.response || "";

        // 🚀 Step 4: Check Guardrails on LLM Response
        const outputGuardrailMatches = await checkGuardrail(llmText);

        if (outputGuardrailMatches.matched) {
            return res.json({
                warning: `⚠️ Guardrail breached in output!`,
                matched_text: outputGuardrailMatches.matched_text,
                similarity_score: outputGuardrailMatches.similarity_score
            });
        }

        res.json({ response: llmText });

    } catch (error) {
        console.error("Error fetching from LLM:", error);
        res.status(500).json({ error: "Error communicating with LLM." });
    }
});

app.listen(3000, () => console.log("✅ Server running on port 3000"));