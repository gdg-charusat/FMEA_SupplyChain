# FMEA Generator API - Postman Testing Guide

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install flask flask-cors
```

### 2. Start API Server
```bash
python api.py
```

Server will start at: **http://localhost:5000**

---

## 📋 API Endpoints

### 1. Health Check
**GET** `/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "FMEA Generator API"
}
```

---

### 2. Generate FMEA from Text
**POST** `/api/fmea/text`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "texts": [
    "Brake system failed completely while driving on highway at 70 mph. Unable to stop properly.",
    "Engine overheated and seized. No warning lights appeared before failure.",
    "Transmission slipping during acceleration. Gear changes are rough and delayed."
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "count": 3,
  "data": [
    {
      "Failure Mode": "Brake system failure",
      "Effect": "Unable to stop vehicle",
      "Cause": "Component wear",
      "Component": "Brake System",
      "Severity": 10,
      "Occurrence": 7,
      "Detection": 8,
      "Rpn": 560,
      "Action Priority": "Critical"
    }
  ]
}
```

---

### 3. Generate FMEA from File
**POST** `/api/fmea/file`

**Body (form-data):**
- `file`: (file) Upload CSV or Excel
- `type`: (text) "structured" or "unstructured"

**Example for Structured File:**
```
file: FMEA.csv
type: structured
```

**Example for Unstructured File:**
```
file: reviews.csv
type: unstructured
```

**Response:**
```json
{
  "status": "success",
  "count": 161,
  "data": [...]
}
```

---

### 4. Generate Hybrid FMEA
**POST** `/api/fmea/hybrid`

**Body (form-data):**
- `file`: (file) Structured CSV/Excel (optional)
- `texts`: (text) JSON array of strings (optional)

**Example:**
```
file: FMEA.csv
texts: ["Brake failure on highway", "Engine overheated"]
```

**Response:**
```json
{
  "status": "success",
  "count": 163,
  "data": [...]
}
```

---

### 5. Export FMEA
**POST** `/api/fmea/export`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "data": [
    {
      "Failure Mode": "Brake failure",
      "Effect": "Unable to stop",
      "Cause": "Worn pads",
      "Component": "Brake System",
      "Severity": 10,
      "Occurrence": 7,
      "Detection": 8,
      "Rpn": 560,
      "Action Priority": "Critical"
    }
  ],
  "format": "excel"
}
```

**Response:** Downloads Excel/CSV file

---

### 6. Get Statistics
**POST** `/api/stats`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "data": [
    {
      "Failure Mode": "Brake failure",
      "Severity": 10,
      "Occurrence": 7,
      "Detection": 8,
      "Rpn": 560,
      "Action Priority": "Critical"
    },
    {
      "Failure Mode": "Engine overheat",
      "Severity": 9,
      "Occurrence": 6,
      "Detection": 7,
      "Rpn": 378,
      "Action Priority": "High"
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "statistics": {
    "total_failures": 2,
    "critical_count": 1,
    "high_count": 1,
    "medium_count": 0,
    "low_count": 0,
    "avg_rpn": 469.0,
    "max_rpn": 560,
    "min_rpn": 378,
    "avg_severity": 9.5,
    "avg_occurrence": 6.5,
    "avg_detection": 7.5
  }
}
```

---

## 🧪 Testing in Postman

### Method 1: Import Collection (Easiest)

1. Open Postman
2. Click **Import** button
3. Select `FMEA_API.postman_collection.json`
4. All endpoints will be ready to test!

### Method 2: Manual Setup

#### Test 1: Health Check
1. Create new request
2. Method: **GET**
3. URL: `http://localhost:5000/health`
4. Click **Send**
5. ✅ Should return `{"status": "healthy"}`

#### Test 2: Generate from Text
1. Create new request
2. Method: **POST**
3. URL: `http://localhost:5000/api/fmea/text`
4. Headers: `Content-Type: application/json`
5. Body → raw → JSON:
```json
{
  "texts": [
    "Brake failure on highway",
    "Engine overheated"
  ]
}
```
6. Click **Send**
7. ✅ Should return FMEA data

#### Test 3: Upload File
1. Create new request
2. Method: **POST**
3. URL: `http://localhost:5000/api/fmea/file`
4. Body → form-data:
   - Key: `file` (change type to File)
   - Value: Select your CSV/Excel file
   - Key: `type`
   - Value: `structured`
5. Click **Send**
6. ✅ Should return FMEA data

---

## 📊 Sample Test Data

### Sample Text Input
```json
{
  "texts": [
    "Hydraulic cylinder leaking fluid due to damaged seal ring causing system failure",
    "Motor temperature extremely high, bearing damage suspected, motor will be damaged",
    "Gas turbine starter has low efficiency and fails to turn engine on starting"
  ]
}
```

### Sample CSV Structure (Structured)
```csv
failure_mode,effect,cause,component
Brake system failure,Cannot stop vehicle,Worn brake pads,Brake System
Engine overheating,Engine damage,Coolant leak,Cooling System
Transmission slip,Poor acceleration,Low fluid level,Transmission
```

### Sample CSV Structure (Unstructured)
```csv
Review
The brake system failed completely while driving on the highway
Engine overheated and seized without warning
Transmission is slipping during acceleration
```

---

## 🔒 Security Limits

| Limit | Value |
|-------|-------|
| Max File Size | 50 MB |
| Max Text Entries | 1,000 |
| Max Batch Processing | 5,000 |

---

## ⚠️ Error Responses

### File Too Large
```json
{
  "error": "File too large. Max: 50 MB"
}
```

### Too Many Entries
```json
{
  "error": "Too many entries. Max: 1000"
}
```

### No Data Provided
```json
{
  "error": "No texts provided"
}
```

---

## 🎯 Testing Workflow

### Complete Test Sequence:

1. **Health Check** → Verify API is running
2. **Generate from Text** → Test text processing
3. **Upload Structured File** → Test file upload
4. **Get Statistics** → Test analytics
5. **Export to Excel** → Test export functionality

---

## 📝 Postman Environment Variables (Optional)

Create environment with:
```
BASE_URL: http://localhost:5000
```

Then use: `{{BASE_URL}}/api/fmea/text`

---

## 🐛 Troubleshooting

### Issue: Connection Refused
**Solution:** Make sure API server is running (`python api.py`)

### Issue: 500 Internal Server Error
**Solution:** Check server logs in terminal for detailed error

### Issue: File Upload Fails
**Solution:** 
- Verify file size < 50 MB
- Check file format (CSV, XLSX, XLS)
- Ensure `type` parameter is set correctly

---

## 📞 Support

For issues or questions:
- Check server logs in terminal
- Verify request format matches examples
- Ensure all dependencies are installed

---

## 🎉 Quick Test Commands (cURL)

### Health Check
```bash
curl http://localhost:5000/health
```

### Generate from Text
```bash
curl -X POST http://localhost:5000/api/fmea/text \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Brake failure on highway"]}'
```

### Upload File
```bash
curl -X POST http://localhost:5000/api/fmea/file \
  -F "file=@FMEA.csv" \
  -F "type=structured"
```

---

**Ready to test! 🚀**
