const fs = require('fs');
const path = require('path');

const guiMain = path.join(__dirname, 'Gui', 'dist', 'src', 'main', 'index.js');

if (!fs.existsSync(guiMain)) {
  console.error('Sara Agent GUI is not built yet.');
  console.error('Run: cd Gui && npm run build');
  process.exit(1);
}

require(guiMain);
