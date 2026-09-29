# Enhanced Research Discovery and Analytics Platform

An institutional research discovery, indexing, and analytics platform integrated with **Kabale University's Institutional Digital Repository (DSpace)**.

## Overview

This platform provides researchers, students, faculty, and academic administrators with a modern, fast, and intuitive discovery layer over academic literature, faculty publications, theses, dissertations, and institutional datasets.

### Key Capabilities
- **Advanced Academic Search**: Full-text keyword search, Boolean querying, faceted filtering by faculty, collection, publication year, author, and peer-review status.
- **Institutional Repository Integration**: Synchronizes directly with Kabale University's DSpace REST backend (`https://backend.kab.ac.ug/server/api`).
- **Researcher Profiles & Metrics**: Author directories, publication counts, citation statistics, and faculty affiliations.
- **Analytics & Trends**: Interactive charts showing publication velocity over time, faculty output breakdowns, and open-access coverage.
- **Administrative Portal**: Sync management, DSpace health diagnostics, schema indexing controls, and synchronization logs.
- **Export & Citation Tools**: Export citations in BibTeX, APA, MLA, and RIS formats, with direct download and permalink access to DSpace items.

---

## Tech Stack

- **Frontend**: React 19, TypeScript, Tailwind CSS, Lucide Icons, Motion
- **Backend / API**: Node.js + Express (serving the frontend and proxying API endpoints) & Django REST Framework / SQLite (metadata storage and DSpace sync service)
- **Tooling**: Vite 6, TSX, esbuild

---

## Getting Started

### Prerequisites
- **Node.js**: v18+ or v20+
- **npm** or **bun**
- **Python**: 3.10+ (with `pip`)

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure configuration keys match your local or production environment.

### 3. Install Dependencies
```bash
# Install Node dependencies
npm install

# Install Python requirements for DSpace synchronization & Django
pip install -r requirements.txt
```

### 4. Database Setup & Migrations
```bash
python3 manage.py migrate
```

### 5. Run the Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Building for Production

```bash
npm run build
npm start
```

---

## License
Developed for Kabale University Institutional Digital Repository.
