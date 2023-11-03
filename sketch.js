let plugInfo
let roomToCycle, cycleToRoom
let configAsTable, configAsDict
let roomNames

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
  textAlign(CENTER,CENTER)
}

let albatrosStatus = 1
let pumpsStatus = { 1: 0, 2: 1, 3: 1, 4: 0 }
let roomSettings = { 1: 20, 2: 21, 3: 20, 4: 16, 5: 16, 6: 21, 7: 16, 8: 16, 9: 16, 10: 18, 11: 22 }
let roomStatuses = { 1: 20, 2: 25, 3: 7, 4: 16, 5: 20, 6: 22, 7: 24, 8: 14, 9: 15, 10: 18, 11: 20 }
let roomTempMax = 30
let roomTempMin = 8

function draw() {
  background(229/255,222/255,202/255)

  var pipeThickness = sqrt(width * height) * 0.011
  var cyclePipeLength = 0.45
  var pumpXPositionOffset = 0.05
  var roomYPositionOffset = 0.4

  var xDir = { 1: 1, 2: 1, 3: -1, 4: -1 }
  var yPos = { 1: 0.55, 2: 0.1, 3: 0.1, 4: 0.55 }

  for (const cycle of [1, 2, 3, 4]) {
    let cycleState = pumpsStatus[cycle] * albatrosStatus
    stroke(cycleState, 0, 1 - cycleState)
    strokeWeight(pipeThickness)
    line(width * 0.5, height * yPos[cycle], width * (0.5 + xDir[cycle] * map(cycleToRoom[cycle].length, 0.25, cycleToRoom[cycle].length + 0.5, 0.1, cyclePipeLength)), height * yPos[cycle])
    stroke(albatrosStatus, 0, 1 - albatrosStatus)
    line(width * 0.5, height * yPos[cycle], width * (0.5 + xDir[cycle] * pumpXPositionOffset), height * yPos[cycle])
    drawPump(width * (0.5 + xDir[cycle] * pumpXPositionOffset), height * yPos[cycle], pumpsStatus[cycle])

    for (var roomOnCycle = 0; roomOnCycle < cycleToRoom[cycle].length; roomOnCycle++) {
      stroke(cycleState, 0, 1 - cycleState)
      strokeWeight(pipeThickness)
      line(
        width * (0.5 + xDir[cycle] * map(roomOnCycle + 1, 0.25, cycleToRoom[cycle].length + 0.5, 0.1, cyclePipeLength)),
        height * yPos[cycle],
        width * (0.5 + xDir[cycle] * map(roomOnCycle + 1, 0.25, cycleToRoom[cycle].length + 0.5, 0.1, cyclePipeLength)),
        height * (yPos[cycle] + map(roomOnCycle + 1, 0, cycleToRoom[cycle].length + 1, 0, roomYPositionOffset))
      )

      noStroke()
      fill(map(roomStatuses[cycleToRoom[cycle][roomOnCycle]], roomTempMin, roomTempMax, 0, 1), 0, 1 - map(roomStatuses[cycleToRoom[cycle][roomOnCycle]], roomTempMin, roomTempMax, 0, 1))
      rect(
        width * (0.5 + xDir[cycle] * map(roomOnCycle + 1, 0.25, cycleToRoom[cycle].length + 0.5, 0.1, cyclePipeLength)),
        height * (yPos[cycle] + map(roomOnCycle + 1, 0, cycleToRoom[cycle].length + 1, 0, roomYPositionOffset)),
        width * 0.06,
        width * 0.06
      )
      fill(map(roomSettings[cycleToRoom[cycle][roomOnCycle]], roomTempMin, roomTempMax, 0, 1), 0, 1 - map(roomSettings[cycleToRoom[cycle][roomOnCycle]], roomTempMin, roomTempMax, 0, 1))
      rect(
        width * (0.5 + xDir[cycle] * map(roomOnCycle + 1, 0.25, cycleToRoom[cycle].length + 0.5, 0.1, cyclePipeLength)),
        height * (yPos[cycle] + map(roomOnCycle + 1, 0, cycleToRoom[cycle].length + 1, 0, roomYPositionOffset)),
        width * 0.035,
        width * 0.035
      )

      fill(0)
      textSize(20)
      text(
        roomNames[cycleToRoom[cycle][roomOnCycle]],
        width * (0.5 + xDir[cycle] * map(roomOnCycle + 1, 0.25, cycleToRoom[cycle].length + 0.5, 0.1, cyclePipeLength)),
        height * (yPos[cycle] + map(roomOnCycle + 1, 0, cycleToRoom[cycle].length + 1, 0, roomYPositionOffset) + 0.09)
      )
    }
  }

  stroke(albatrosStatus, 0, 1 - albatrosStatus)
  strokeWeight(pipeThickness)
  line(width * 0.5, height * 0.85, width * 0.5, height * yPos[2])


  fill(albatrosStatus, 0, 1 - albatrosStatus)
  rect(width * 0.5, height * 0.8, width * 0.08, width * 0.08)
  fill(0)
  noStroke()
  textSize(20)
  text(
    "Albatros",
    width*0.5,
    height*0.925
  )
}

function drawPump(posX, posY, state) {
  var w = width * 0.007;
  var l = width * 0.05;
  stroke(0)
  strokeWeight(5)
  fill(0)
  if (state == 0) {
    rect(posX, posY, w, l)
  }
  else {
    rect(posX, posY, l, w)
  }
  stroke(0)
  fill(0)
  ellipse(posX, posY, width * 0.018, width * 0.018)
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight)
}

function findKeysWithSpecificValue(obj, valueToFind) {
  return Object.entries(obj).filter(([key, value]) => value === valueToFind).map(([key]) => {
    if (!isNaN(key)) return Number(key)
    return key
  })
}

function processTableIntoDict(table) {
  let csvDictionary = {}

  for (let r = 0; r < table.getRowCount(); r++) {
    let key = table.getString(r, 0); // Get the first column data
    let value = table.getString(r, 1); // Get the second column data
    csvDictionary[key] = value;
  }

  return csvDictionary
}