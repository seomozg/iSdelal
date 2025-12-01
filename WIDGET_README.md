# AI Chat Widget

A modern, responsive AI chat widget for websites that integrates with your RAG (Retrieval-Augmented Generation) system.

## Features

- 🚀 **Modern UI**: Clean, responsive design with smooth animations
- 🌍 **Multi-language**: Built-in English and Russian support
- 🎨 **Customizable**: Extensive configuration options
- 📱 **Mobile-friendly**: Optimized for all screen sizes
- 🔧 **Developer-friendly**: Simple API for integration
- ⚡ **Fast**: Lightweight and optimized performance

## Quick Start

### 1. Basic Integration

Add this code to your website's `<head>` or before `</body>`:

```html
<script>
// Local development (ready to use)
window.AIWidgetConfig = {
  apiBase: 'http://localhost:8000',
  collection: 'court_craze',
  apiKey: 'aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5'
};
</script>
<script src="http://localhost:8000/widget/widget.js"></script>
```

### 2. Configuration

```javascript
window.AIWidgetConfig = {
  // API Settings
  apiBase: 'http://localhost:8000',              // Base URL (without /api, change for production)
  apiKey: 'aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5', // Your API key
  collection: 'court_craze',                     // Available: court_craze, joyreactor_single, wba_exsportia, tbank

  // UI Settings
  title: 'AI Assistant',                         // Widget title
  placeholder: 'Ask me anything...',             // Input placeholder
  position: 'bottom-right',                      // Position: bottom-right, bottom-left, top-right, top-left
  theme: 'default',                              // Theme: default, dark
  language: 'en',                                // Language: en, ru

  // Behavior
  welcomeMessage: 'Hello! How can I help?',      // Auto-show welcome message
  maxMessages: 50                                // Message history limit
};
```

## API Methods

### Initialize
```javascript
AIWidget.init({
  title: 'New Title',
  collection: 'new_collection'
});
```

### Send Message
```javascript
AIWidget.sendMessage('Hello AI!');
```

### Toggle Widget
```javascript
AIWidget.toggle();
```

### Check Status
```javascript
console.log(AIWidget.isOpen()); // true/false
```

## Styling

The widget loads its own CSS automatically. For custom styling:

```css
/* Custom widget styles */
.ai-widget-card {
  border-radius: 20px !important;
}

.ai-widget-toggle {
  background: linear-gradient(45deg, #ff6b6b, #4ecdc4) !important;
}
```

## Collections Available

Your system has these ingested collections ready to use:

- **`court_craze`** - Padel tennis information from court-craze-info.lovable.app (13 chunks) ✅
- **`joyreactor_multi`** - JoyReactor entertainment content from joyreactor.cc (16 chunks) ⭐ **ENHANCED**
- **`tbank_multi`** - T-Bank comprehensive banking services (14 chunks) ⭐ **ENHANCED**

**Try these example questions:**

**Padel Tennis** (`court_craze`):
- "What is padel tennis?"
- "What tournaments are mentioned?"

**Banking** (`tbank_multi`) ⭐ **RECOMMENDED**:
- "What services does T-Bank offer?"
- "What investment options are available?"
- "How do I open an investment account?"

**Entertainment** (`joyreactor_multi`) ⭐ **RECOMMENDED**:
- "What is JoyReactor?"
- "What are some popular tags and categories?"
- "What kind of content can I find?"

## Testing

To test the widget locally:

1. Start your Docker containers: `docker compose up`
2. Open `widget_example.html` in your browser
3. The widget should appear in the bottom-right corner

## Files

- `widget/widget.js` - Main widget JavaScript
- `widget/widget.css` - Widget styles
- `widget_example.html` - Integration example
- `WIDGET_README.md` - This documentation

## Browser Support

- Chrome 70+
- Firefox 70+
- Safari 12+
- Edge 79+

## Troubleshooting

### Widget not appearing
- Check that the script is loaded after DOM is ready
- Verify the API endpoint is accessible
- Check browser console for errors

### API errors
- Ensure the API key is correct
- Verify the collection name exists
- Check network connectivity

### Styling issues
- Make sure no CSS conflicts with `.ai-widget-*` classes
- Use `!important` for custom overrides if needed

## License

This widget is part of your RAG system implementation.
