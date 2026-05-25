# 🏆 Condensed 3-Minute Demo Script

## 🎤 Part 1: The Hook & Intro (45 Seconds)

**Speaker:**
> "In large enterprises, knowledge is scattered across thousands of disconnected PDFs and policies. The biggest risk isn't losing a document—it's when documents silently **contradict** each other.
>
> Imagine an engineering team deploying a system based on an approved 'Implementation Guide,' completely unaware that a recent 'Security Audit' explicitly blocks it. Standard AI tools miss this because they only read text; they don't understand dependencies.
> 
> Today we present the **Autonomous Knowledge Intelligence Platform**. It’s an AI brain that ingests documents and automatically maps their operational relationships into a living Knowledge Graph—flagging compliance risks and blockers before they happen."

---

## 💻 Part 2: The Live Demo (2 Minutes)

### Step 1: Real-time Ingestion
*Navigate to the **Ingest** page.*

**Speaker:**
> "Let's upload four documents from a real enterprise scenario: A data policy (v1), an updated policy (v2), an engineering implementation guide, and a recent security audit."

*Action: Upload the 4 new test PDFs.*

**Speaker:**
> "As they upload, our pipeline chunks the text, extracts key entities, and uses LLMs to mathematically deduce the operational relationships between these distinct files in real-time."

### Step 2: Extracting Insights from the Graph
*Navigate to the **Knowledge Graph** page. Click **Refresh**.*

**Speaker:**
> "Here is our Knowledge Graph. This isn't just a visualization; it's an interactive map of operational reality. 
> 
> Look at the colored lines connecting the documents:
> - The green line shows that the Engineering Guide **IMPLEMENTS** Policy v2.
> - But more importantly, the red line shows that the Security Audit formally **BLOCKS** the Engineering Guide!
>
> By toggling the Edge Filters at the top, or turning on the **Risk Map**, executives can instantly visualize bottlenecks and compliance risks without having to read a single PDF."

### Step 3: Hallucination Resistance (Query)
*Navigate to the **Query** page.*

**Speaker:**
> "Let's ask the AI: **'Can we deploy Project Titan to production?'**"

*Action: Type the query and hit enter.*

**Speaker:**
> "A standard chatbot would say 'Yes.' But our engine traverses the Knowledge Graph. It sees the implementation guide, follows the red line to the security audit, and correctly warns us that deployment is **blocked** due to a failing AWS integration. 
>
> It even provides exact citations below. We've built a strict Hallucination Resistance Layer—if it can't prove it using the graph, it won't answer."

---

## 🚀 Part 3: The Conclusion (15 Seconds)

**Speaker:**
> "We are transforming dead file storage into an active intelligence engine. Our platform eliminates compliance blind spots, accelerates engineering, and provides mathematical trust. Thank you."
