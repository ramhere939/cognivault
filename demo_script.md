# 🏆 Hackathon Winning Demo Script: Autonomous Knowledge Intelligence Platform

This script is designed for a **3 to 5 minute pitch**. It is structured to hook the judges, prove the technical complexity, and leave them with a clear understanding of the business value.

---

## 🎤 Part 1: The Pitch & The Problem (1 minute)

**Speaker:**
> "In large enterprises, knowledge doesn't live in a single database—it's scattered across thousands of PDFs, policies, and audit reports. The biggest risk isn't that you can't *find* a document. The risk is that documents silently **contradict** each other.
> 
> Imagine an engineering team deploying a new system based on *Policy v2*, while completely unaware that a recent *Security Audit* explicitly blocks that deployment. Standard search engines and basic AI chatbots can't catch this. They just summarize text.
>
> Today we are presenting the **Autonomous Knowledge Intelligence Platform**. It doesn't just read documents; it understands their operational dependencies. It automatically builds a dynamic Knowledge Graph that maps out exactly how every policy, contract, and audit interacts, flagging compliance risks before they become disasters."

---

## 💻 Part 2: The Live Demo (2-3 minutes)

*Before the demo, ensure your database is completely empty so the judges see the magic happen from scratch.*

### Step 1: Real-time Ingestion
*Navigate to the **Ingest** page.*

**Speaker:**
> "Let's see this in action. I'm going to upload four documents from an enterprise scenario: An old data policy (v1), a new data policy (v2), an engineering implementation guide, and a recent security audit."

*Action: Drag and drop the 4 new test PDFs (`acme_policy_v1.pdf`, `acme_policy_v2.pdf`, `acme_implementation_guide.pdf`, `acme_security_audit.pdf`) and click Upload.*

**Speaker:**
> "As these upload, our AI pipeline is doing heavy lifting. It's not just extracting text. It is chunking the data, generating vector embeddings, extracting key entities, and using LLMs to mathematically deduce the relationships between these distinct files in real-time."

### Step 2: The Knowledge Graph
*Navigate to the **Knowledge Graph** page. Click **Refresh** if needed.*

**Speaker:**
> "This is where the magic happens. What you're seeing isn't a static diagram—it's a living map of the organization's operational state."

*Action: Point out the colored lines.*
**Speaker:**
> "Notice how the system automatically discovered that Policy v2 **SUPERSEDES** (orange line) Policy v1. 
> It also detected that the Engineering Guide **IMPLEMENTS** (green line) Policy v2.
> But most importantly, look at this red line: The system read the Security Audit and deduced that it formally **BLOCKS** the Engineering Guide."

*Action: Toggle the Edge Filters at the top (e.g., turn off SUPERSEDES, then turn it back on) to show how you can isolate specific dependency chains.*

### Step 3: Risk Heatmap
*Action: Click the **Risk Map** toggle at the top of the graph.*

**Speaker:**
> "When managing thousands of documents, finding the critical blockers is hard. By enabling the Risk Heatmap, the platform instantly highlights nodes that are compromised or actively blocked—alerting executives to immediate compliance risks."

### Step 4: Grounded Q&A (Hallucination Resistance)
*Navigate to the **Query** page.*

**Speaker:**
> "Now, let's see how an engineer would interact with this. Let's ask: **'Can we deploy Project Titan to production?'**"

*Action: Type the query: "Can we deploy Project Titan to production?" and hit enter.*

**Speaker:**
> "A standard AI would just read the Implementation Guide and say 'Yes, go ahead.' But our engine traverses the Knowledge Graph. It sees the implementation guide, traces the dependency to the security audit, and warns the user that deployment is currently **blocked** due to a failing AWS KMS integration."

*Action: Point out the **Citations** below the answer.*
**Speaker:**
> "Every claim is backed by a strict citation. We've built a Hallucination Resistance Layer—if the AI can't prove it using the ingested documents, it refuses to answer."

---

## 🚀 Part 3: The Conclusion & Value Prop (30 seconds)

**Speaker:**
> "In summary, our platform transforms dead file storage into an active intelligence engine. 
> 
> By running this platform, enterprises can:
> 1. Eliminate compliance blind spots.
> 2. Accelerate engineering by untangling bureaucratic red tape.
> 3. Trust their AI, thanks to mathematical trust scores and graph-backed citations.
> 
> We are bringing true, autonomous operational awareness to the enterprise. Thank you."

---

## 📝 Demo Checklist (Do this right before you present)
- [ ] Make sure your backend and frontend are running (`uvicorn app.main:app --reload` and `npm run dev`).
- [ ] Go to the frontend and delete any old documents to start with a clean slate.
- [ ] Have the 4 specific `acme_*.pdf` files ready in an easy-to-reach folder.
- [ ] Rehearse clicking through the UI while speaking to ensure your timing matches the script.
