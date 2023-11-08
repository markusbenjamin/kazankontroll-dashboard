var plugInfo
var roomToCycle, cycleToRoom
var configAsTable, configAsDict
var roomNames
var sketchAspectRatio
var toolTip
var noOfControlledRooms

function setup() {
  let canvas = createCanvas(windowWidth, windowHeight)
  sketchAspectRatio = 2.125
  enforceAspectRatio(sketchAspectRatio)
  canvas.parent('canvas-container')
  noFill()
  noStroke()
  colorMode(RGB, 1)
  strokeCap(PROJECT)
  rectMode(CENTER)
  textAlign(CENTER, CENTER)
  textFont('Consolas')
  toolTip = new ToolTipBox()

  updateConfig()

  listenToFirebase('systemState', (data) => {
    console.log("System state change detected.")
    updateState(data)
  })

  listenToFirebase('decisions', (data) => {
    console.log("Decision detected.")
    readDecisions(data)
  })

  listenToFirebase('updates/config/seenByRaspi', (data) => {
    console.log("Config updated detected.")
    if (data['seenByDashboard'] == false) {
      updateConfig()
    }
  })
}

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

//Dummy values so no startup error occurs
var albatrosStatus = 0
var pumpStatuses = { 1: 0, 2: 0, 3: 0, 4: 0 }
var roomSettings = { 1: 1, 2: 21, 3: 20, 4: 16, 5: 16, 6: 21, 7: 16, 8: 16, 9: 16, 10: 22, 11: 22 }
var roomStatuses = { 1: 0.5, 2: 25, 3: 12, 4: 16, 5: 20, 6: 22, 7: 24, 8: 14, 9: 15, 10: 17, 11: 20 }
var externalTempAllow = 0

function updateState(dataFromFirebase) {
  albatrosStatus = dataFromFirebase['albatrosStatus']
  pumpStatuses = dataFromFirebase['pumpStatuses']
  roomSettings = dataFromFirebase['roomSettings']
  roomStatuses = dataFromFirebase['roomStatuses']
  externalTempAllow = dataFromFirebase['externalTempAllow']
}

function updateConfig() {
  // loadTable is an asynchronous function
  loadTable('https://docs.google.com/spreadsheets/d/e/2PACX-1vSEiiNYdSFXxQInKCrERcHkEKH-MVJuglz2XHnUhEZvR4SBcrw85MU5X-ioQFmaF25lMGJZWkXSfWN5/pub?output=csv', 'csv', 'header', function (table) {
    // This callback function will be called once the table is loaded
    configAsDict = processTableIntoDict(table);
    roomToCycle = {};

    for (var room = 1; room <= configAsDict['no_of_controlled_rooms']; room++) {
      roomToCycle[room] = parseInt(configAsDict['room_' + room + '_plug']);
    }

    cycleToRoom = {};
    for (const cycle of [1, 2, 3, 4]) {
      cycleToRoom[cycle] = findKeysWithSpecificValue(roomToCycle, cycle);
    }

    roomNames = {};
    for (var room = 1; room <= configAsDict['no_of_controlled_rooms']; room++) {
      roomNames[room] = configAsDict['room_' + room];
    }

    noOfControlledRooms = configAsDict['no_of_controlled_rooms']

    updateDataInFirebase('updates/config/seenByDashboard', true)
  });
}

function loadLogs() {
  //For loading system logs from repo for time based plots  
}

var decisions

function readDecisions(dataFromFirebase) {
  decisions = dataFromFirebase
}

var problematicCount, wantHeatingCount

function draw() {
  try {
    drawStateVisualization()
    drawInfoBox()

    manageToolTip()
  } catch (error) {
    console.log(error.message);
  }
}

function parseTimestampToList(timestamp) {
  let month = parseInt(timestamp.substring(0, 2), 10);
  let day = parseInt(timestamp.substring(3, 5), 10);
  let hour = parseInt(timestamp.substring(7, 9), 10);
  let minute = parseInt(timestamp.substring(10, 12), 10);
  return [month, day, hour, minute];
}

function findLatestMessage(messages) {
  let latestMessage = messages.reduce((latest, current) => {
    let latestTimestampList = parseTimestampToList(latest.timestamp);
    let currentTimestampList = parseTimestampToList(current.timestamp);
    for (let i = 0; i < currentTimestampList.length; i++) {
      if (currentTimestampList[i] > latestTimestampList[i]) {
        return current;
      } else if (currentTimestampList[i] < latestTimestampList[i]) {
        return latest;
      }
    }
    return latest; // If all components are equal, return the latest (first encountered)
  }, messages[0] || { 'message': '', 'timestamp': '01.01. 00:00' });

  return latestMessage;
}

var allDecisionMessages

function drawInfoBox() {
  stroke(0)
  strokeWeight(2)
  var x = width * 0.185
  var y = height * 0.75
  var w = width * 0.275
  var h = height * 0.375
  rect(x, y, w, h, width * 0.01)


  allDecisionMessages = []
  var how = decisions['albatros']['reason'] === 'vote' ? 'normál\nüzemmenetben' : '\ndirektben'
  var to = decisions['albatros']['decision'] >= 1 ? 'be' : 'ki'
  var albatrosMessage = {
    'message': 'Kazánok ' + how + ' ' + to + 'kapcsolva.',
    'timestamp': decisions['albatros']['timestamp']
  }
  allDecisionMessages.push(albatrosMessage)

  var cycleMessages = []
  for (var cycle = 1; cycle < 5; cycle++) {
    var who = ['1-es', '2-es', '3-mas', '4-es'][cycle - 1]
    var how = decisions['cycle'][cycle]['reason'] === 'vote' ? 'normál\nüzemmenetben' : '\ndirektben'
    var to = decisions['cycle'][cycle]['decision'] == 0 ? 'ki' : 'be'
    cycleMessages[cycle] = {
      'message': who + ' kör ' + how + ' ' + to + 'kapcsolva.',
      'timestamp': decisions['cycle'][cycle]['timestamp']
    }
    allDecisionMessages.push(cycleMessages[cycle])
  }

  var aboveOrBelow = decisions['externalTempAllow']['reason'] == 'above' ? 'fölé' : 'alá'
  var onOrOff = decisions['externalTempAllow']['decision'] == 0 ? 'ki' : 'be'
  var externalTempMessage = {
    'message': 'Külső hőmérséklet határ ' + aboveOrBelow + ',\nfűtés ' + onOrOff + 'kapcsolva.',
    'timestamp': decisions['externalTempAllow']['timestamp']
  }
  allDecisionMessages.push(externalTempMessage)

  var latestMessage
  try {
    latestMessage = findLatestMessage(allDecisionMessages)
  }
  catch (error) {
    latestMessage = { 'message': '' }
  }

  var messages = [
    externalTempAllow == 1 ?
      (wantHeatingCount == 0 ? "Senki nem kér fűtést." : "Fűtést kér: " + wantHeatingCount + " helyiség.") :
      ("Határérték feletti kinti\nhőmérséklet miatt nincs fűtés."),
    externalTempAllow == 1 && wantHeatingCount > 0 ?
      (problematicCount == 0 ? "Nincs problémás helyiség." : "Eltérések száma: " + problematicCount + " (" + round(100 * problematicCount / noOfControlledRooms) + "%)") : "",
    "Utolsó esemény:\n" + parseTimestampToList(latestMessage['timestamp'])[2] + ":" + (parseTimestampToList(latestMessage['timestamp'])[3] < 10 ? "0" : "") + parseTimestampToList(latestMessage['timestamp'])[3] + " - " + latestMessage['message']
  ].filter(element => element !== '')

  fill(0)
  noStroke()
  textSize(width * 0.014)
  text(
    messages.join('\n\n'),
    x, y)
}

function manageToolTip() {
  toolTip.draw()
  toolTip.hide()
}

function drawStateVisualization() {
  problematicCount = 0
  wantHeatingCount = 0
  background(229 / 255, 222 / 255, 202 / 255)
  setDrawingParameters()
  drawCycles()
  drawPipingAndBoiler()
}

function setDrawingParameters() {
  roomTempMax = 30
  roomTempMin = 10
  roomTempDiffTolerance = 2
  pipeThickness = sqrt(width * height) * 0.0075
  cyclePipeLength = 0.55
  pumpXPositionOffset = 0.04
  roomXPositionOffset = -0.015 //not in width scale!
  roomYPositionOffset = 0.08

  cycleXDir = { 1: 1, 2: 1, 3: -1, 4: -1 }
  cycleYPos = { 1: 0.575, 2: 0.05, 3: 0.05, 4: 0.575 }
}

function drawCycles() {
  for (const cycle of [1, 2, 3, 4]) {
    var cycleState = pumpStatuses[cycle] * albatrosStatus * externalTempAllow
    var cycleColor = color(cycleState, 0, 1 - cycleState)

    stroke(cycleColor)
    strokeWeight(pipeThickness)
    line(width * 0.5, height * cycleYPos[cycle], width * (0.5 + cycleXDir[cycle] * map(cycleToRoom[cycle].length - 1 + roomXPositionOffset, 0, cycleToRoom[cycle].length, 0.1, cyclePipeLength)), height * cycleYPos[cycle])
    stroke(albatrosStatus, 0, 1 - albatrosStatus)
    line(width * 0.5, height * cycleYPos[cycle], width * (0.5 + cycleXDir[cycle] * pumpXPositionOffset), height * cycleYPos[cycle])
    drawPump(width * (0.5 + cycleXDir[cycle] * pumpXPositionOffset), height * cycleYPos[cycle], pumpStatuses[cycle], cycle)

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

  var roomSummedStatus = roomSetting * externalTempAllow

  if (roomSetting == 0 || roomSetting == 1) {
    fill(0)
    rect(x, y + h / 2, w * 0.3, h * 0.25)

    strokeWeight(width * 0.005)
    stroke(1)
    line(x - w * 0.1, y + 1.025 * h / 2, x + width * 0.0325 * cos(TWO_PI * 0.125 - PI / 2 * roomSummedStatus), y + 1.025 * h / 2 + width * 0.0325 * sin(TWO_PI * 0.125 - PI / 2 * roomSummedStatus))
    fill(1)
    noStroke()
    ellipse(x + width * 0.0325 * cos(TWO_PI * 0.125 - PI / 2 * roomSummedStatus), y + 1.025 * h / 2 + width * 0.0325 * sin(TWO_PI * 0.125 - PI / 2 * roomSummedStatus), width * 0.01, width * 0.01)
    stroke(0)
    line(x - w * 0.1, y + h / 2, x + width * 0.0325 * cos(TWO_PI * 0.125 - PI / 2 * roomSummedStatus), y + h / 2 + width * 0.0325 * sin(TWO_PI * 0.125 - PI / 2 * roomSummedStatus))
    fill(0)
    noStroke()
    ellipse(x + width * 0.0325 * cos(TWO_PI * 0.125 - PI / 2 * roomSummedStatus), y + h / 2 + width * 0.0325 * sin(TWO_PI * 0.125 - PI / 2 * roomSummedStatus), width * 0.01, width * 0.01)

    fill(1)
    noStroke()
    rect(x - w / 4, y + h / 2, w * 0.3, h * 0.25)

    fill(0.75)
    stroke(0)
    strokeWeight(1.5)
    rect(x * 1.00125, (y + h * 0.2) * 1.00125, w * 0.725, w * 0.65)
    noStroke()
    rect(x * 1.0, (y + h * 0.2) * 1.0, w * 0.725, w * 0.65)
    textSize(width * 0.016)
    fill(0, roomSummedStatus == 1 ? 1 : 0.125)
    text("be", x * 1.00065, (y + h * 0.2) * 1.0025)
    fill(1, 0, 0, roomSummedStatus == 1 ? 1 : 0.125)
    text("be", x * 1.0005, (y + h * 0.2) * 1.001)


    fill(0.75)
    stroke(0)
    strokeWeight(1.5)
    rect(x * 1.00125, (y + h * 0.8) * 1.00125, w * 0.725, w * 0.65)
    noStroke()
    rect(x * 1.0, (y + h * 0.8) * 1.0, w * 0.725, w * 0.65)
    textSize(width * 0.016)
    fill(0, roomSummedStatus == 0 ? 1 : 0.125)
    text("ki", x * 1.00065, (y + h * 0.8) * 1.0025)
    fill(0, 0, 1, roomSummedStatus == 0 ? 1 : 0.125)
    text("ki", x * 1.0005, (y + h * 0.8) * 1.001)
  }
  else {
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
    text(round(roomStatus), x + w * 1.2, y + map(roomTempMax - roomStatus + roomTempMin, roomTempMin, roomTempMax, 0, h))
    textStyle(NORMAL)
  }

  stroke(cycleColor)
  strokeWeight(pipeThickness / 2)
  line(x - w / 2, y, x + w / 2, y)
  line(x - w / 2, y + h, x + w / 2, y + h)

  noStroke()
  fill(229 / 255, 222 / 255, 202 / 255)
  rect(x, y - h * 0.125, w * 2.5, h * 0.14)
  noStroke()

  if (roomSummedStatus == 1 || roomSetting - roomStatus > 1) {
    wantHeatingCount += 1
  }

  var problematic = false

  if (roomSetting == 0 || roomSetting == 1) {
    if (roomSummedStatus != cycleState) {
      problematicCount += 1
      problematic = true
      if (mouseOver(x, y + h / 2, w, h)) {
        toolTip.show(cycleState == 1 ? 'Nem kéri, mégis fűtünk.' : 'Kéri, mégsincs fűtés.')
      }
    }
  }
  else if (cycleState == 0 && roomStatus < roomSetting - roomTempDiffTolerance) {
    problematicCount += 1
    problematic = true
    if (mouseOver(x, y + h / 2, w, h)) {
      toolTip.show('Hideg van, mégsincs fűtés.')
    }
  }
  else if (cycleState == 1 && roomStatus > roomSetting + roomTempDiffTolerance) {
    problematicCount += 1
    problematic = true
    if (mouseOver(x, y + h / 2, w, h)) {
      toolTip.show('Meleg van, mégis fűtünk.')
    }
  }
  if (problematic) {
    fill(1 * cycleState, 0, 1 * (1 - cycleState), 0.075)
    rect(x, y - h * 0.125, w * 2.5, h * 0.14)
  }

  fill(0)
  textSize(width * 0.013)
  text(roomName, x, y - h * 0.125)
}

function drawFlame(x, y, w, h, colOuter, colInner, outer) {
  push();
  translate(x, y);
  fill(colOuter);
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
    drawFlame(x, y - h * 0.05, w * 0.6, h * 0.5, colInner, colInner, false)
  }
}

function drawPipingAndBoiler() {
  var x = width * 0.5
  var y = height * (cycleYPos[1] + cycleYPos[2]) / 2
  var w = width * 0.054
  var h = width * 0.09

  if (mouseOver(x, y, w, h)) {
    var how = decisions['albatros']['reason'] === 'vote' ? 'normál\nüzemmenetben' : 'direktben'
    var to = decisions['albatros']['decision'] > 0 ? 'be' : 'ki'
    toolTip.show('Kazánok ' + how + ' ' + to + 'kapcsolva.\n(' + decisions['albatros']['timestamp'] + ')')
  }

  stroke(albatrosStatus, 0, 1 - albatrosStatus)
  strokeWeight(pipeThickness)
  line(width * 0.5, height * cycleYPos[1], width * 0.5, height * cycleYPos[2])

  noStroke()
  strokeWeight(pipeThickness)
  stroke(albatrosStatus, 0, 1 - albatrosStatus)

  fill(1)
  rect(x, y, w, h, width * 0.01)
  fill(0.2)
  noStroke()
  rect(width * 0.5, 1.1 * height * (cycleYPos[1] + cycleYPos[2]) / 2, 0.65 * width * 0.055, 0.65 * width * 0.0175)
  if (albatrosStatus == 1) {
    let wiggleAmount = 0.016
    drawFlame(width * 0.5 * 0.99, 1.16 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.095 * random(1 - wiggleAmount, 1 + wiggleAmount), width * 0.055 * random(1 - wiggleAmount, 1 + wiggleAmount), color(1, 0.5, 0, 0.875), color(1, 1, 0, 0.9), true)
    drawFlame(width * 0.5 * 1.01, 1.16 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.095 * 0.85 * random(1 - wiggleAmount, 1 + wiggleAmount), width * 0.055 * 0.85 * random(1 - wiggleAmount, 1 + wiggleAmount), color(1, 0.5, 0, 0.875), color(1, 1, 0, 0.9), true)
  }
  else {
    let wiggleAmount = 0.035
    for (var n = 0; n < 10; n++) {
      drawFlame(width * 0.5+map(n,0,9,-w/3.75,w/3.75), 1.125 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.0195 * random(1 - wiggleAmount, 1 + wiggleAmount), width * 0.01 * random(1 - wiggleAmount, 1 + wiggleAmount), color(128 / 255, 234 / 255, 237 / 255, 0.875), color(47 / 255, 118 / 255, 200 / 255, 0.9), true)
    }
  }

  fill(albatrosStatus, 0, 1 - albatrosStatus)
  fill(1)
  rect(width * 0.5, 1.155 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.005 + width * 0.035, width * 0.005 + width * 0.005)
}

function drawPump(x, y, state, cycle) {
  var w = width * 0.0045;
  var l = width * 0.035;

  if (mouseOver(x, y, l * 1.1, l * 1.1)) {
    var who = ['1-es', '2-es', '3-mas', '4-es'][cycle - 1]
    var how = decisions['cycle'][cycle]['reason'] === 'vote' ? 'normál\nüzemmenetben' : 'direktben'
    var to = decisions['cycle'][cycle]['decision'] == 0 ? 'ki' : 'be'
    toolTip.show(who + ' kör ' + how + '\n' + to + 'kapcsolva.\n(' + decisions['cycle'][cycle]['timestamp'] + ')')
  }

  stroke(0)
  strokeWeight(2)
  fill(0)
  if (state == 0) {
    rect(x, y, w, l)
    ellipse(x, y + l / 2, width * 0.0165 * 0.6, width * 0.0165 * 0.3)
    ellipse(x, y - l / 2, width * 0.0165 * 0.6, width * 0.0165 * 0.3)
  }
  else {
    rect(x, y, l, w)
    ellipse(x + l / 2, y, width * 0.0165 * 0.3, width * 0.0165 * 0.6)
    ellipse(x - l / 2, y, width * 0.0165 * 0.3, width * 0.0165 * 0.6)
  }
  strokeWeight(2)
  stroke(0)
  fill(0)
  ellipse(x, y, width * 0.01, width * 0.01)
  stroke(1)
  fill(1)
  ellipse(x, y, width * 0.01 * 0.25, width * 0.01 * 0.25)
}

function mouseOver(centerX, centerY, w, h) {
  // Calculate the top-left corner based on the center coordinates
  let topLeftX = centerX - w / 2;
  let topLeftY = centerY - h / 2;

  // Check if the mouse is inside the rectangle
  if (mouseX >= topLeftX && mouseX <= topLeftX + w &&
    mouseY >= topLeftY && mouseY <= topLeftY + h) {
    return true; // The mouse is over the rectangle
  } else {
    return false; // The mouse is not over the rectangle
  }
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

class ToolTipBox {
  constructor() {
    this.text = "";
    this.isVisible = false;
    this.padding = width * 0.0075;
    this.textSize = width * 0.0125;
    this.borderColor = color(0)
    this.fillColor = color(1);
    this.textColor = color(0);
  }

  // Call this function to display the tooltip with the provided text
  show(text) {
    this.text = text;
    this.isVisible = true;
  }

  // Call this function to hide the tooltip
  hide() {
    this.isVisible = false;
    cursor()
  }

  draw() {
    if (this.isVisible) {
      noCursor()
      // Set the text properties
      textSize(this.textSize);
      let txtWidth = multiLineTextWidth(this.text) + this.padding * 2;
      let txtHeight = this.textSize + this.padding * 2 * (1 + (this.text.match(/\n/g) || []).length);

      // Determine the position of the tooltip so it doesn't hang off the edge
      let posX = mouseX + txtWidth / 2; // Offset from mouse position
      let posY = mouseY + txtHeight / 2;

      // Adjust if it's going out of the canvas
      if (posX + txtWidth > width) {
        posX = width - txtWidth;
      }
      if (posY + txtHeight > height) {
        posY = height - txtHeight;
      }

      stroke(this.borderColor);
      strokeWeight(2)
      rect(posX, posY, txtWidth, txtHeight, 4);

      // Draw the tooltip background
      fill(this.fillColor);
      noStroke();
      rect(posX, posY, txtWidth, txtHeight, 4); // Slight rounding for aesthetics

      // Draw the tooltip text
      fill(this.textColor);
      text(this.text, posX, posY);
    }
  }
}

function multiLineTextWidth(text) {
  // Split the text by new lines
  const lines = text.split('\n');

  // Map each line to its width
  const widths = lines.map(line => textWidth(line));

  // Return the maximum width
  return max(widths);
}
