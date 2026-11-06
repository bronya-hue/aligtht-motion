const express = require('express')
const path = require('path')
const apiRoutes = require('./app/api/route')

const app = express()

app.use(require('cors')())
app.use(express.json())
app.use(express.urlencoded({ extended: true }))
app.use(express.static(path.join(__dirname, 'public'), {
  etag: true,
  lastModified: true,
  setHeaders: (res, filePath) => {
    if (filePath.endsWith('.html') || filePath.endsWith('.css') || filePath.endsWith('.js')) {
      res.setHeader('Cache-Control', 'no-cache, must-revalidate')
    }
  }
}))

app.use('/api', apiRoutes)

// ...
const PORT = process.env.PORT || 3300;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Backend listening on 0.0.0.0:${PORT}`);
});
