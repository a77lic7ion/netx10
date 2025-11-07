# NetIntelliX10

An intelligent network monitoring and analysis platform.

## Overview

NetIntelliX10 is a comprehensive network intelligence platform designed to provide real-time monitoring, device management, and analytics for modern network infrastructures.

## Features

- **Real-time Network Monitoring**: Monitor network devices and traffic in real-time
- **Device Management**: Discover, track, and manage network devices
- **Analytics Dashboard**: Visualize network performance and trends
- **Alert System**: Get notified of network issues and anomalies
- **AI-Powered Insights**: Intelligent analysis and recommendations

## Technology Stack

- **Backend**: Node.js with Express.js
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Database**: SQLite (development), PostgreSQL (production)
- **Real-time**: WebSocket for live updates
- **Charts**: Chart.js for data visualization

## Project Structure

```
netx10/
├── server.js          # Main server file
├── package.json       # Project dependencies
├── public/           # Static files
│   ├── index.html   # Main dashboard
│   ├── css/         # Stylesheets
│   └── js/          # Client-side JavaScript
├── routes/          # API routes
├── models/          # Data models
└── utils/           # Utility functions
```

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the server:
   ```bash
   npm start
   ```

3. Open your browser and navigate to `http://localhost:3000`

## Development

- Run in development mode: `npm run dev`
- Run tests: `npm test`

## License

MIT License