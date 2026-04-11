const express = require('express');
const cors = require('cors');
const path = require('path');
const db = require('./database');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Serve frontend static files
app.use(express.static(path.join(__dirname, 'frontend')));

// API Routes
app.get('/api/bills', (req, res) => {
    db.all("SELECT * FROM bills ORDER BY id DESC", [], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json({ data: rows });
    });
});

app.post('/api/bills', (req, res) => {
    const { month, year, state, units, total, energy, fixed, tax, surcharge } = req.body;
    db.run(`INSERT INTO bills (month, year, state, units, total, energy, fixed, tax, surcharge) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [month, year, state, units, total, energy, fixed, tax, surcharge],
        function(err) {
            if (err) {
                return res.status(500).json({ error: err.message });
            }
            res.json({ message: "success", id: this.lastID });
        });
});

app.delete('/api/bills', (req, res) => {
    db.run("DELETE FROM bills", function(err) {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json({ message: "success", changes: this.changes });
    });
});

// Fallback to index.html for SPA-like behaviour
app.use((req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'index.html'));
});

// Start Server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
