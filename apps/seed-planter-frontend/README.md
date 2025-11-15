# SeedGPT Sandbox Frontend

Modern React application providing an intuitive interface for the SeedGPT sandbox demo experience.

## Overview

The Sandbox Frontend allows users to describe project ideas and watch in real-time as AI generates complete project structures, issues, and pull requests - demonstrating AutoGrow's capabilities before users commit resources.

## Features

- **Real-time Progress**: Live updates via WebSocket connection
- **Modern UI**: Built with React 18, TailwindCSS, and Lucide icons
- **Responsive Design**: Works seamlessly on desktop and mobile
- **Error Handling**: Graceful error handling with user-friendly messages
- **Fast Development**: Vite for instant HMR and optimized builds

## Tech Stack

- **React 18**: Modern React with hooks
- **Vite**: Next-generation frontend tooling
- **TailwindCSS**: Utility-first CSS framework
- **Lucide React**: Beautiful icon library
- **WebSocket**: Real-time communication

## Setup

### Prerequisites

- Node.js 18+ and npm
- Running Sandbox API (see `sandbox-api/README.md`)

### Installation

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env if API is not on localhost:8000
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

The app will be available at `http://localhost:3000`

## Available Scripts

- `npm run dev` - Start development server with HMR
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint

## Project Structure

```
sandbox-frontend/
├── src/
│   ├── App.jsx              # Main application component
│   ├── main.jsx             # Application entry point
│   ├── index.css            # Global styles with Tailwind
│   └── hooks/
│       └── useSandbox.js    # Custom hook for sandbox operations
├── index.html               # HTML template
├── package.json             # Dependencies and scripts
├── vite.config.js           # Vite configuration
└── tailwind.config.js       # Tailwind configuration
```

## Components

### App.jsx
Main application component featuring:
- Project idea input form
- Real-time progress visualization
- Status step indicators
- Results display with links to GitHub

### useSandbox Hook
Custom React hook managing:
- Sandbox creation API calls
- WebSocket connection lifecycle
- Progress state management
- Error handling

## Configuration

### Environment Variables

Create `.env` file:
```env
VITE_API_URL=http://localhost:8000
```

### Tailwind Configuration

Customize theme in `tailwind.config.js`:
```javascript
theme: {
  extend: {
    colors: {
      primary: {
        // Your brand colors
      },
    },
  },
}
```

## Development

### Hot Module Replacement
Vite provides instant HMR - changes appear immediately without full page reload.

### Component Development
```jsx
import { Sparkles } from 'lucide-react'

function MyComponent() {
  return (
    <div className="card">
      <Sparkles className="w-5 h-5 text-primary-600" />
      <h2>Hello World</h2>
    </div>
  )
}
```

### Custom Hooks
```javascript
import { useSandbox } from './hooks/useSandbox'

function MyComponent() {
  const { createSandbox, progress, error } = useSandbox()
  
  // Use sandbox functionality
}
```

## Building for Production

1. **Build the app**:
   ```bash
   npm run build
   ```

2. **Preview build**:
   ```bash
   npm run preview
   ```

3. **Deploy** the `dist/` folder to your hosting provider

## Deployment

### Netlify
```bash
# Build command
npm run build

# Publish directory
dist
```

### Vercel
```bash
# Framework preset: Vite
# Build command: npm run build
# Output directory: dist
```

### Static Hosting
Upload the `dist/` folder to any static hosting service (S3, GitHub Pages, etc.)

## WebSocket Connection

The app connects to the Sandbox API via WebSocket for real-time updates:

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/sandboxes/${id}/ws`)

ws.onmessage = (event) => {
  const progress = JSON.parse(event.data)
  // Update UI with progress
}
```

## Styling

### TailwindCSS Utilities
```jsx
<button className="btn-primary">
  Click Me
</button>

<div className="card">
  Content
</div>

<input className="input-field" />
```

### Custom Classes
Defined in `src/index.css`:
- `.btn-primary` - Primary button style
- `.card` - Card container
- `.input-field` - Form input style

## Troubleshooting

### Common Issues

**App won't start**:
- Check Node.js version (18+)
- Delete `node_modules` and run `npm install`
- Check port 3000 is available

**WebSocket connection fails**:
- Verify API is running on correct port
- Check CORS configuration in API
- Verify `VITE_API_URL` in `.env`

**Build fails**:
- Clear Vite cache: `rm -rf node_modules/.vite`
- Check for TypeScript errors
- Verify all dependencies are installed

**Styles not working**:
- Ensure TailwindCSS is properly configured
- Check PostCSS configuration
- Verify `index.css` is imported in `main.jsx`

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile browsers: iOS Safari 12+, Chrome Android

## Performance

- **Code Splitting**: Automatic with Vite
- **Tree Shaking**: Removes unused code
- **Asset Optimization**: Images and CSS optimized
- **Lazy Loading**: Components loaded on demand

## License

Part of the SeedGPT project.
