const axios = require('axios');
axios.get('http://localhost:8000/parties/').then(r => console.log("DATA TYPE:", typeof r.data, "DATA:", r.data)).catch(e => console.log("ERROR:", e.response.status, e.response.data));
