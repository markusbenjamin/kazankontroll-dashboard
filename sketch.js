var plugInfo
var roomToCycle, cycleToRoom
var configAsTable, configAsDict
var roomNames
var canvas, textBox
var roomNameTextBoxes

function preload() {
  // Load the CSV file and set it to be comma-separated
  plugInfo = loadTable('data_and_config/plug_info.csv', 'csv', 'header')
  configAsTable = loadTable('data_and_config/config_safe.csv', 'csv', 'header')
}

var sketchAspectRatio

function setup() {
  canvas = createCanvas(windowWidth, windowHeight)
  sketchAspectRatio = 2
  enforceAspectRatio(sketchAspectRatio)
  canvas.parent('canvas-container')
  noFill()
  noStroke()
  colorMode(RGB, 1)
  strokeCap(PROJECT)
  rectMode(CENTER)
  textAlign(CENTER, CENTER)
  textFont('Consolas Black')

  roomToCycle = {}
  for (const row of plugInfo.getRows()) {
    roomToCycle[int(row.obj['room'])] = int(row.obj['num'])
  }

  cycleToRoom = {}
  for (const cycle of [1, 2, 3, 4]) {
    cycleToRoom[cycle] = findKeysWithSpecificValue(roomToCycle, cycle)
  }

  configAsDict = processTableIntoDict(configAsTable)

  roomNames = {}
  roomNameTextBoxes = {}
  for (var room = 1; room <= configAsDict['no_of_controlled_rooms']; room++) {
    roomNames[room] = configAsDict['room_' + str(room)]
    roomNameTextBoxes[room] = new TextBox(-1, -1, -1, -1)
  }

  listenToFirebase('/test', (data) => {
    console.log(data)
    // Do something with the data
  });
}


var albatrosStatus = 1
var pumpsStatus = { 1: 1, 2: 1, 3: 0, 4: 0 }
var roomSettings = { 1: 20, 2: 21, 3: 20, 4: 16, 5: 16, 6: 21, 7: 16, 8: 16, 9: 16, 10: 22, 11: 22 }
var roomStatuses = { 1: 21, 2: 25, 3: 12, 4: 16, 5: 20, 6: 22, 7: 24, 8: 14, 9: 15, 10: 17, 11: 20 }

var roomTempMax
var roomTempMin
var roomTempDiffTolerance
var pipeThickness
var cyclePipeLength
var pumpXPositionOffset
var roomXPositionOffset
var roomYPositionOffset
var cycleXDir
var cycleYPos

function draw() {
  background(229 / 255, 222 / 255, 202 / 255)

  roomTempMax = 30
  roomTempMin = 10
  roomTempDiffTolerance = 2
  pipeThickness = sqrt(width * height) * 0.0075
  cyclePipeLength = 0.55
  pumpXPositionOffset = 0.04
  roomXPositionOffset = -0.015 //not in width scale!
  roomYPositionOffset = 0.09

  cycleXDir = { 1: 1, 2: 1, 3: -1, 4: -1 }
  cycleYPos = { 1: 0.575, 2: 0.05, 3: 0.05, 4: 0.575 }

  drawCycles()
  drawPiping()
  //drawFlame(width / 2, height *0.9, 3*400, 3*200, color(0))
}

function drawCycles() {
  for (const cycle of [1, 2, 3, 4]) {
    var cycleState = pumpsStatus[cycle] * albatrosStatus
    var cycleColor = color(cycleState, 0, 1 - cycleState)

    stroke(cycleColor)
    strokeWeight(pipeThickness)
    line(width * 0.5, height * cycleYPos[cycle], width * (0.5 + cycleXDir[cycle] * map(cycleToRoom[cycle].length - 1 + roomXPositionOffset, 0, cycleToRoom[cycle].length, 0.1, cyclePipeLength)), height * cycleYPos[cycle])
    stroke(albatrosStatus, 0, 1 - albatrosStatus)
    line(width * 0.5, height * cycleYPos[cycle], width * (0.5 + cycleXDir[cycle] * pumpXPositionOffset), height * cycleYPos[cycle])
    drawPump(width * (0.5 + cycleXDir[cycle] * pumpXPositionOffset), height * cycleYPos[cycle], pumpsStatus[cycle])

    for (var roomOnCycle = 0; roomOnCycle < cycleToRoom[cycle].length; roomOnCycle++) {
      var roomNumber = cycleToRoom[cycle][roomOnCycle]
      var roomX = width * (0.5 + cycleXDir[cycle] * map(roomOnCycle + roomXPositionOffset, 0, cycleToRoom[cycle].length, 0.1, cyclePipeLength))
      var roomSetting = roomSettings[roomNumber]
      var roomStatus = roomStatuses[roomNumber]
      var roomSettingNormalized = map(roomSetting, roomTempMin, roomTempMax, 0, 1)
      var roomStatusNormalized = map(roomStatus, roomTempMin, roomTempMax, 0, 1)
      var roomSettingColor = color(roomSettingNormalized, 0, 1 - roomSettingNormalized)
      var roomStatusColor = color(roomStatusNormalized, 0, 1 - roomStatusNormalized)
      var roomBaseSize = width * 0.1
      var roomY = height * (cycleYPos[cycle] + roomYPositionOffset)
      var roomName = roomNames[roomNumber]

      stroke(cycleColor)
      strokeWeight(pipeThickness)
      line(
        roomX,
        height * cycleYPos[cycle],
        roomX,
        roomY
      )

      drawRoom(roomX, roomY, roomBaseSize * 0.3, roomBaseSize * 1.6, roomStatus, roomSetting, roomStatusNormalized, roomSettingNormalized, roomStatusColor, roomSettingColor, cycleColor, cycleState, roomName, roomNumber)
    }
  }
}

function drawRoom(x, y, w, h, roomStatus, roomSetting, roomStatusNormalized, roomSettingNormalized, roomStatusColor, roomSettingColor, cycleColor, cycleState, roomName, roomNumber) {
  fill(1)
  noStroke()
  rect(x, y + h / 2, w, h)

  for (var temp = roomTempMin + 1; temp <= roomTempMax - 1; temp += 1) {
    if (temp % 5 == 0) {
      strokeWeight(2)
      stroke(0, 0.75)
      line(x - w / 2, y + map(temp, roomTempMin, roomTempMax, 0, h), x, y + map(temp, roomTempMin, roomTempMax, 0, h))
      noStroke()
      fill(0)
      textSize(width * 0.01)
      text(roomTempMax - temp + roomTempMin, x + w / 4, y + map(temp, roomTempMin, roomTempMax, 0, h))
    }
    else {
      strokeWeight(1)
      stroke(0, 0.5)
      line(x - w / 2, y + map(temp, roomTempMin, roomTempMax, 0, h), x, y + map(temp, roomTempMin, roomTempMax, 0, h))
      noStroke()
      fill(0, 0.75)
      textSize(width * 0.0075)
    }
  }

  noStroke()
  fill(roomSettingColor)
  rect(x, y + h * (1 - roomSettingNormalized), w * 1.25, h * 0.025)
  textSize(width * 0.017)
  textStyle(BOLD)
  text(roomSetting, x - w * 1.2, y + map(roomTempMax - roomSetting + roomTempMin, roomTempMin, roomTempMax, 0, h))

  noStroke()
  fill(1)
  ellipse(x, y + h * (1 - roomStatusNormalized), 1.25 * w / 2.5, 1.25 * w / 2.5)
  topRect(x, y + h * (1 - roomStatusNormalized), 1.8 * w / 6, h * roomStatusNormalized)
  fill(roomStatusColor)
  ellipse(x, y + h * (1 - roomStatusNormalized), w / 2.5, w / 2.5)
  topRect(x, y + h * (1 - roomStatusNormalized), w / 6, h * roomStatusNormalized)
  textSize(width * 0.017)
  text(roomStatus, x + w * 1.2, y + map(roomTempMax - roomStatus + roomTempMin, roomTempMin, roomTempMax, 0, h))
  textStyle(NORMAL)

  stroke(cycleColor)
  strokeWeight(pipeThickness / 2)
  line(x - w / 2, y, x + w / 2, y)
  line(x - w / 2, y + h, x + w / 2, y + h)

  noStroke()
  fill(229 / 255, 222 / 255, 202 / 255)
  rect(x, y - h * 0.125, w * 2.5, h * 0.14)
  if ((cycleState * 2 - 1) * (roomStatus - roomSetting) > roomTempDiffTolerance) {
    noStroke()
    fill(1 * cycleState, 0, 1 * (1 - cycleState), 0.075)
    rect(x, y - h * 0.125, w * 2.5, h * 0.14)
  }
  fill(0)
  textSize(width * 0.013)
  text(roomName, x, y - h * 0.125)
}

function drawFlame(x, y, w, h, col, outer) {
  push();
  translate(x, y);
  fill(col);
  noStroke();
  beginShape();

  // Draw right side of the flame using the given function and mirror for left side
  for (let i = 0; i <= 1; i += 0.01) {
    let flameX = (1 / 5) * pow(-1 + i, 2) * i * (-5 + 4 * i) * w;
    let flameY = -h * i;
    vertex(flameX, flameY);
  }

  // Draw the left side as a mirrored version of the right side
  for (let i = 1; i >= 0; i -= 0.01) {
    let flameX = -(1 / 5) * pow(-1 + i, 2) * i * (-5 + 4 * i) * w;
    let flameY = -h * i;
    vertex(flameX, flameY);
  }

  endShape(CLOSE);
  pop();

  if (outer) {
    drawFlame(x, y - h * 0.05, w * 0.6, h * 0.5, color(1, 1, 0, 0.9), false)
  }
}

function drawPiping() {
  stroke(albatrosStatus, 0, 1 - albatrosStatus)
  strokeWeight(pipeThickness)
  line(width * 0.5, height * cycleYPos[1], width * 0.5, height * cycleYPos[2])

  noStroke()
  strokeWeight(pipeThickness)
  stroke(albatrosStatus, 0, 1 - albatrosStatus)
  fill(1)
  rect(width * 0.5, height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.054, width * 0.09, 20)
  fill(0.2)
  noStroke()
  rect(width * 0.5, 1.1 * height * (cycleYPos[1] + cycleYPos[2]) / 2, 0.65 * width * 0.055, 0.65 * width * 0.0175)
  if (albatrosStatus == 1) {
    let wiggleAmount = 0.015
    drawFlame(width * 0.5 * 0.99, 1.16 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.095 * random(1 - wiggleAmount, 1 + wiggleAmount), width * 0.055 * random(1 - wiggleAmount, 1 + wiggleAmount), color(1, 0.5, 0, 0.875), true)
    drawFlame(width * 0.5 * 1.01, 1.16 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.095 * 0.85 * random(1 - wiggleAmount, 1 + wiggleAmount), width * 0.055 * 0.85 * random(1 - wiggleAmount, 1 + wiggleAmount), color(1, 0.5, 0, 0.875), true)
  }
  fill(albatrosStatus, 0, 1 - albatrosStatus)
  fill(1)
  rect(width * 0.5, 1.18 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.005 + width * 0.035, width * 0.005 + width * 0.015)
}

function drawPump(posX, posY, state) {
  var w = width * 0.0035;
  var l = width * 0.03;
  stroke(0)
  strokeWeight(2)
  fill(0)
  if (state == 0) {
    rect(posX, posY, w, l)
    ellipse(posX, posY + l / 2, width * 0.0165 * 0.55, width * 0.0165 * 0.2)
    ellipse(posX, posY - l / 2, width * 0.0165 * 0.55, width * 0.0165 * 0.2)
  }
  else {
    rect(posX, posY, l, w)
    ellipse(posX + l / 2, posY, width * 0.0165 * 0.2, width * 0.0165 * 0.55)
    ellipse(posX - l / 2, posY, width * 0.0165 * 0.2, width * 0.0165 * 0.55)
  }
  strokeWeight(2)
  stroke(0)
  fill(0)
  ellipse(posX, posY, width * 0.01, width * 0.01)
  stroke(1)
  fill(1)
  ellipse(posX, posY, width * 0.01 * 0.25, width * 0.01 * 0.25)
}

function topRect(x, y, w, h) {
  rectMode(CORNER)
  let adjustedX = x - w / 2;
  let adjustedY = y;
  rect(adjustedX, adjustedY, w, h);
  rectMode(CENTER)
}

function enforceAspectRatio(aspectRatio) {
  let newWidth, newHeight;

  // Calculate the aspect ratio based on the current window dimensions
  let windowRatio = windowWidth / windowHeight;
  let desiredRatio = aspectRatio;

  // Adjust the canvas size based on the aspect ratio
  if (windowRatio > desiredRatio) {
    // Window is wider than the desired ratio, so the height is the constraining dimension
    newHeight = windowHeight;
    newWidth = newHeight * desiredRatio;
  } else {
    // Window is narrower than the desired ratio, so the width is the constraining dimension
    newWidth = windowWidth;
    newHeight = newWidth / desiredRatio;
  }

  // Resize the canvas to fit the new dimensions while maintaining the aspect ratio
  resizeCanvas(newWidth, newHeight);
}

function windowResized() {
  enforceAspectRatio(sketchAspectRatio)
}

function findKeysWithSpecificValue(obj, valueToFind) {
  return Object.entries(obj).filter(([key, value]) => value === valueToFind).map(([key]) => {
    if (!isNaN(key)) return Number(key)
    return key
  })
}

function processTableIntoDict(table) {
  var csvDictionary = {}

  for (var r = 0; r < table.getRowCount(); r++) {
    var key = table.getString(r, 0); // Get the first column data
    var value = table.getString(r, 1); // Get the second column data
    csvDictionary[key] = value;
  }

  return csvDictionary
}

class TextBox {
  constructor(x, y, w, h) {
    // Initialize with default values
    this.centerX = x;
    this.centerY = y;
    this.w = w || 100; // default width if not provided
    this.h = h || 50;  // default height if not provided
    // Default style properties
    this.textToDisplay = ['Default Text'];
    this.fontSizes = [16];
    this.URLs = ['#'];
    this.borderColor = 'rgba(0, 0, 0, 0)';
    this.fillColor = 'rgba(255, 255, 255, 0)';
    this.hAlign = 'center';
    this.vAlign = 'center';
    this.boxCreated = false; // Flag to indicate if the box has been created
  }

  setStyle(canvas, x, y, w, h, textToDisplay, fontSizes, URLs, borderColor, fillColor, fontColor, hAlign, vAlign) {
    // Set style properties from arguments
    this.centerX = x;
    this.centerY = y;
    this.w = w;
    this.h = h;
    this.textToDisplay = textToDisplay || this.textToDisplay;
    this.fontSizes = fontSizes || this.fontSizes;
    this.URLs = URLs || this.URLs;
    this.borderColor = borderColor || this.borderColor;
    this.fillColor = fillColor || this.fillColor;

    this.hAlign = hAlign || this.hAlign;
    this.vAlign = vAlign || this.vAlign;

    // If the box hasn't been created yet, create it
    if (!this.boxCreated) {
      this.box = this.createBox();
      this.boxCreated = true;
    }

    this.box.style('font-family', 'Arial, sans-serif'); // Set font family to Arial
    this.box.style('color', fontColor);

    // Update styles and position
    this.updateStyle(canvas);
  }

  createBox() {
    let box = createDiv('');
    // Set styles that are not dependent on the parameters
    box.style('padding', '20px');
    box.style('box-sizing', 'border-box');
    box.style('overflow', 'auto');
    box.style('display', 'flex');
    box.style('flex-direction', 'column');
    return box;
  }

  updateStyle(canvas) {
    // Apply the updated styles to the box
    this.box.style('background-color', this.fillColor);
    this.box.style('border', `1px solid ${this.borderColor}`);
    this.box.size(this.w, this.h);

    // Align items based on the provided horizontal and vertical alignment
    this.box.style('align-items', this.hAlign === 'center' ? 'center' : (this.hAlign === 'right' ? 'flex-end' : 'flex-start'));
    this.box.style('justify-content', this.vAlign === 'center' ? 'center' : (this.vAlign === 'bottom' ? 'flex-end' : 'flex-start'));

    // Remove all existing child elements
    this.box.html('');

    // Create text elements (and links if URLs are provided)
    for (let i = 0; i < this.textToDisplay.length; i++) {
      let text = this.textToDisplay[i];
      let fontSize = this.fontSizes[i];
      let url = this.URLs[i];
      let element;

      if (url) {
        // If there's a URL, create a link
        element = createA(url, text, '_blank');
      } else {
        // Just create a text element
        element = createDiv(text);
      }

      // Style the link or text element
      element.style('font-size', `${fontSize}px`);
      element.style('text-align', this.hAlign);
      element.style('color', '#000');
      element.style('text-decoration', 'none');
      element.style('margin', '5px');
      element.parent(this.box);
    }

    // Update the position if the canvas is available
    if (canvas) {
      this.updateBoxPosition(canvas);
    }
    this.setScrollbarVisibility(false);
  }

  updateBoxPosition(canvas) {
    if (this.boxCreated && canvas) {
      const rect = canvas.elt.getBoundingClientRect();
      let topLeftX = this.centerX - this.w / 2 + rect.left;
      let topLeftY = this.centerY - this.h / 2 + rect.top;
      this.box.position(topLeftX, topLeftY);
    }
  }

  setScrollbarVisibility(visible) {
    if (visible) {
      this.box.style('overflow', 'auto');
      // Remove styles that hide scrollbars
      this.box.style('scrollbar-width', null);
      this.box.style('-ms-overflow-style', null);
      this.box.style('::-webkit-scrollbar', null);
    } else {
      this.box.style('overflow', 'scroll'); // Still need to allow scrolling
      // Add styles to hide scrollbars
      this.box.style('scrollbar-width', 'none'); // Firefox
      this.box.style('-ms-overflow-style', 'none'); // IE+Edge

      // Webkit browsers (Chrome, Safari, newer versions of Opera)
      // It's tricky to do pseudo-elements in inline styles; you might need an external stylesheet or inject styles into the head
      let styleSheet = document.createElement('style');
      styleSheet.type = 'text/css';
      styleSheet.innerText = '.no-scrollbar::-webkit-scrollbar { display: none; }';
      document.head.appendChild(styleSheet);
      this.box.addClass('no-scrollbar');
    }
  }
}
