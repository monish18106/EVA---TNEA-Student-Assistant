# EVA – TNEA RAG + LLM Assistant

EVA is a student assistant built using Tamil Nadu Engineering Admissions (TNEA) 2024 data.

The system uses a strict RAG (Retrieval-Augmented Generation) architecture to ensure accuracy and prevent hallucinations.

---

## Features

- Cutoff information by:
  - District
  - Course
  - Category
  - Year (2024)
- College listings by district
- General engineering questions answered using an LLM
- No invented data
- No predictions or recommendations

---

## Architecture

- **RAG (ChromaDB)**  
  Used ONLY for:
  - Cutoff queries
  - College listings

- **LLM (Groq – LLaMA 3.1 8B)**  
  Used ONLY for:
  - General questions (e.g., "What is CSE")

The LLM never generates or modifies cutoff or college data.

---

## Project Structure

