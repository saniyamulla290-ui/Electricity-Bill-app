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

// Get all bills
app.get('/api/bills', (req, res) => {
    db.all('SELECT * FROM bills ORDER BY timestamp DESC', [], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

// Save a new bill
app.post('/api/bills', (req, res) => {
    const { month, year, state, units, total, energy, fixed, tax, surcharge } = req.body;
    
    // UPSERT style: check if exists
    db.get('SELECT id FROM bills WHERE month = ? AND year = ?', [month, year], (err, row) => {
        if (err) return res.status(500).json({ error: err.message });

        if (row) {
            // Update existing
            const sql = `UPDATE bills SET state = ?, units = ?, total = ?, energy = ?, fixed = ?, tax = ?, surcharge = ? WHERE id = ?`;
            db.run(sql, [state, units, total, energy, fixed, tax, surcharge, row.id], function(err) {
                if (err) return res.status(500).json({ error: err.message });
                res.json({ message: 'Bill updated successfully', id: row.id });
            });
        } else {
            // Insert new
            const sql = `INSERT INTO bills (month, year, state, units, total, energy, fixed, tax, surcharge) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`;
            db.run(sql, [month, year, state, units, total, energy, fixed, tax, surcharge], function(err) {
                if (err) return res.status(500).json({ error: err.message });
                res.status(201).json({ message: 'Bill saved successfully', id: this.lastID });
            });
        }
    });
});

// Delete all bills (Clear History)
app.delete('/api/bills', (req, res) => {
    db.run('DELETE FROM bills', function(err) {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json({ message: 'All history cleared', rowsDeleted: this.changes });
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
