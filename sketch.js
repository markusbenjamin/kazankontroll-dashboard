var plugInfo
var roomToCycle, cycleToRoom
var configAsTable, configAsDict
var roomNames

function preload() {
  // Load the CSV file and set it to be comma-separated
  plugInfo = loadTable('data_and_config/plug_info.csv', 'csv', 'header')
  configAsTable = loadTable('data_and_config/config_safe.csv', 'csv', 'header')
}

function setup() {
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
  for (var room = 1; room <= configAsDict['no_of_controlled_rooms']; room++) {
    roomNames[room] = configAsDict['room_' + str(room)]
  }

  createCanvas(windowWidth, windowHeight)
  noFill()
  noStroke()
  colorMode(RGB, 1)
  strokeCap(PROJECT)
  rectMode(CENTER)
  textAlign(CENTER, CENTER)
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

function draw() {
  background(229 / 255, 222 / 255, 202 / 255)

  roomTempMax = 30
  roomTempMin = 10
  roomTempDiffTolerance = 2
  pipeThickness = sqrt(width * height) * 0.007
  cyclePipeLength = 0.55
  pumpXPositionOffset = 0.04
  roomXPositionOffset = -0.015 //not in width scale!
  roomYPositionOffset = 0.09

  var cycleXDir = { 1: 1, 2: 1, 3: -1, 4: -1 }
  var cycleYPos = { 1: 0.55, 2: 0.1, 3: 0.1, 4: 0.55 }

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
      var roomX = width * (0.5 + cycleXDir[cycle] * map(roomOnCycle + roomXPositionOffset, 0, cycleToRoom[cycle].length, 0.1, cyclePipeLength))
      var roomSetting = roomSettings[cycleToRoom[cycle][roomOnCycle]]
      var roomStatus = roomStatuses[cycleToRoom[cycle][roomOnCycle]]
      var roomSettingNormalized = map(roomSetting, roomTempMin, roomTempMax, 0, 1)
      var roomStatusNormalized = map(roomStatus, roomTempMin, roomTempMax, 0, 1)
      var roomSettingColor = color(roomSettingNormalized, 0, 1 - roomSettingNormalized)
      var roomStatusColor = color(roomStatusNormalized, 0, 1 - roomStatusNormalized)
      var roomBaseSize = width * 0.1
      var roomY = height * (cycleYPos[cycle] + roomYPositionOffset)
      var roomName = roomNames[cycleToRoom[cycle][roomOnCycle]]

      stroke(cycleColor)
      strokeWeight(pipeThickness)
      line(
        roomX,
        height * cycleYPos[cycle],
        roomX,
        roomY
      )

      drawRoom(roomX, roomY, roomBaseSize * 0.25, roomBaseSize * 1.6, roomStatus, roomSetting, roomStatusNormalized, roomSettingNormalized, roomStatusColor, roomSettingColor, cycleColor, cycleState, roomName)
    }
  }

  stroke(albatrosStatus, 0, 1 - albatrosStatus)
  strokeWeight(pipeThickness)
  line(width * 0.5, height * 0.85, width * 0.5, height * cycleYPos[2])

  fill(albatrosStatus, 0, 1 - albatrosStatus)
  ellipse(width * 0.5, height * 0.85, width * 0.05, width * 0.05)
  fill(0)
  noStroke()
  textSize(20)
  text(
    "kazánok",
    width * 0.5,
    height * 0.9275
  )
}

function drawRoom(x, y, w, h, roomStatus, roomSetting, roomStatusNormalized, roomSettingNormalized, roomStatusColor, roomSettingColor, cycleColor, cycleState, roomName) {
  if ((cycleState * 2 - 1) * (roomStatus - roomSetting) > roomTempDiffTolerance) {
    noStroke()
    fill(1 * cycleState, 0, 1 * (1 - cycleState), 0.1)
    rect(x, y + h / 2, w * 3.4, h * 1.05)
  }

  fill(1)
  noStroke()
  rect(x, y + h / 2, w, h)
  stroke(cycleColor)
  strokeWeight(pipeThickness / 2)
  line(x - w / 2, y, x + w / 2, y)
  line(x - w / 2, y + h, x + w / 2, y + h)

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
      text(roomTempMax - temp + roomTempMin, x + w / 4, y + map(temp, roomTempMin, roomTempMax, 0, h))
    }
  }

  noStroke()
  fill(roomSettingColor)
  rect(x, y + h * (1 - roomSettingNormalized), w * 1.25, h * 0.025)
  textSize(width * 0.015)
  textStyle(BOLD)
  text(roomSetting, x - w * 1.2, y + map(roomTempMax - roomSetting + roomTempMin, roomTempMin, roomTempMax, 0, h))

  noStroke()
  fill(roomStatusColor)
  ellipse(x, y + h * (1 - roomStatusNormalized), w / 2.5, w / 2.5)
  topRect(x, y + h * (1 - roomStatusNormalized), w / 6, h * roomStatusNormalized)
  textSize(width * 0.015)
  text(roomStatus, x + w * 1.2, y + map(roomTempMax - roomStatus + roomTempMin, roomTempMin, roomTempMax, 0, h))
  textStyle(NORMAL)

  noStroke()
  fill(229 / 255, 222 / 255, 202 / 255)
  rect(x, y - h * 0.125, w * 3, h * 0.125)
  fill(0)
  textSize(width * 0.013)
  text(roomName, x, y - h * 0.125)
}

function drawPump(posX, posY, state) {
  var w = width * 0.007;
  var l = width * 0.05;
  stroke(0)
  strokeWeight(2)
  fill(0)
  if (state == 0) {
    rect(posX, posY, w, l)
  }
  else {
    rect(posX, posY, l, w)
  }
  strokeWeight(2)
  stroke(0)
  fill(0)
  ellipse(posX, posY, width * 0.018, width * 0.018)
  stroke(1)
  fill(1)
  ellipse(posX, posY, width * 0.018 / 4, width * 0.018 / 4)
}

function topRect(x, y, w, h) {
  rectMode(CORNER)
  let adjustedX = x - w / 2;
  let adjustedY = y;
  rect(adjustedX, adjustedY, w, h);
  rectMode(CENTER)
}

function gradientLine(x1, y1, x2, y2, color1, color2) {
  var segments = 20;  // Number of line segments

  for (var i = 0; i < segments; i++) {
    var t = i / segments;
    var tNext = (i + 1) / segments;
    var xStart = x1 + (x2 - x1) * t;
    var yStart = y1 + (y2 - y1) * t;
    var xEnd = x1 + (x2 - x1) * tNext;
    var yEnd = y1 + (y2 - y1) * tNext;

    var r = color1._array[0] + (color2._array[0] - color1._array[0]) * t;
    var g = color1._array[1] + (color2._array[1] - color1._array[1]) * t;
    var b = color1._array[2] + (color2._array[2] - color1._array[2]) * t;

    stroke(r, g, b);
    line(xStart, yStart, xEnd, yEnd);
  }
}

function windowResized() {
  if (windowWidth >= 800 && windowHeight >= 600) {
    resizeCanvas(windowWidth, windowHeight)
  }
  else {
    resizeCanvas(800, 600)
  }
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