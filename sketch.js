var plugInfo
var roomToCycle, cycleToRoom
var configAsTable, configAsDict
var roomNames, bufferZones
var sketchAspectRatio
var toolTip
var noOfControlledRooms
var masterOverrides
var dataSetLoaded

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

  listenToFirebase('updates/config/timestamp', (data) => {
    updateConfig()
  })

  dataSetLoaded = false
}

var roomTempMax
var roomTempMin
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
var roomReachable
var roomLastUpdate

function updateState(dataFromFirebase) {
  albatrosStatus = dataFromFirebase['albatrosStatus']
  pumpStatuses = dataFromFirebase['pumpStatuses']
  roomSettings = dataFromFirebase['roomSettings']
  roomStatuses = dataFromFirebase['roomStatuses']
  externalTempAllow = dataFromFirebase['externalTempAllow']
  roomReachable = dataFromFirebase['roomReachable']
  roomLastUpdate = dataFromFirebase['roomLastUpdate']
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

    bufferZones = {}
    for (var room = 1; room <= configAsDict['no_of_controlled_rooms']; room++) {
      bufferZones[room] = { 'upper': float(configAsDict['buffer_upper_' + room]), 'lower': float(configAsDict['buffer_lower_' + room]) }
    }

    masterOverrides = {}
    for (var cycle = 1; cycle <= 4; cycle++) {
      masterOverrides[cycle] = configAsDict['cycle_' + cycle + '_master_override']
    }

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

var problematicCount, problematicList, wantHeatingCount, wantHeatingList
var roomToDraw = 0 //DEV
function draw() {
  try {
    background(229 / 255, 222 / 255, 202 / 255)
    drawStateVisualization()
    drawInfoBox()

    /*var prevRoom = roomToDraw //DEV
    roomToDraw = round(map(mouseX, 0, width, 1, 7)) //DEV
    if (prevRoom != roomToDraw) { //DEV
      dataSetLoaded = false //DEV
    } //DEV
    textSize(30) //DEV
    noStroke() //DEV
    fill(0) //DEV
    roomToDraw = 4 //DEV
    text(roomToDraw, width * 0.5, height * 0.15) //DEV

    drawTempData(roomToDraw, '2023.11.09', '2023.11.09')*/
    manageToolTip()
  } catch (error) {
    console.log(error.message);
  }
}

var tempData //DEV
function drawTempData(room, fromDate, toDate) {
  // var tempData //DEV
  if (dataSetLoaded == false) {
    loadTempDataForDays(room, fromDate, toDate).then(result => { tempData = result })
    dataSetLoaded = true
  }

  var startDate = tempData[0][0]
  var endDate = tempData[tempData.length - 2][0]
  var totalMinutes = calculateTimeDifferenceInMinutes(startDate, endDate)
  var minMaxTemp = minMax((transposeArray(tempData))[1].map(parseFloat).filter(value => !Number.isNaN(value)))

  noFill()
  stroke(0)
  strokeWeight(5)
  beginShape()
  for (let i = 0; i < tempData.length; i++) {
    point(
      map(calculateTimeDifferenceInMinutes(startDate, tempData[i][0]), 0, totalMinutes, width * 0.25, width * 0.75),
      height - map(tempData[i][1], minMaxTemp[0], minMaxTemp[1], height * 0.1, height * 0.9)
    )
  }
  endShape()

  var timeWindow = round(map(mouseY, 0, height, 2, 24)) * 5
  timeWindow = 60
  textSize(30) //DEV
  noStroke() //DEV
  fill(0) //DEV
  text(frameRate(), width * 0.5, height * 0.05) //DEV

  noFill()
  stroke(1, 0, 0)
  strokeWeight(3)
  beginShape()

  //Sonoff szobáknak: simítás aztán nem-lineáris interpoláció
  //Tuya szobáknak: nem-lineáris interpoláció
  //legyen több szobás adatstruktúra
  //adat betöltése és előkészítése csak egyszer a nézet megnyitásakor

  for (let i = 0; i < tempData.length; i++) {
    // Define symmetric time window around current data point
    let windowData = tempData.filter((_, j) =>
      Math.abs(calculateTimeDifferenceInMinutes(tempData[i][0], tempData[j][0])) <= timeWindow / 2
    );

    let weightedSum = 0;
    let totalWeight = 0;
    let currentTimestamp = tempData[i][0];

    // Apply weights and calculate weighted sum and total weight
    for (let [timestamp, value] of windowData) {
      const weight = timeWindow / 2 - Math.abs(calculateTimeDifferenceInMinutes(currentTimestamp, timestamp));
      weightedSum += parseFloat(value) * weight;
      totalWeight += weight;
    }

    // Calculate average and ensure at least some data was in the window
    const average = (totalWeight > 0) ? (weightedSum / totalWeight) : parseFloat(tempData[i][1]);
    vertex(
      map(calculateTimeDifferenceInMinutes(startDate, tempData[i][0]), 0, totalMinutes, width * 0.25, width * 0.75),
      height - map(average, minMaxTemp[0], minMaxTemp[1], height * 0.1, height * 0.9)
    )
  }

  endShape()
}

async function loadTempDataForDays(room, startDate, endDate) {
  var daysInRange = getDaysInRange(parseTimestampWithYearToDict(startDate), parseTimestampWithYearToDict(endDate))

  var paths = []
  for (const dataDay of daysInRange) {
    paths.push("measured_temps/" + [dataDay['year'], dataDay['month'], dataDay['day']].map(zeroPaddedString).join('_') + "/room_" + room + ".csv")
  }

  for (const path of paths) {
    console.log(paths.length)
  }

  var tempData = await loadAndConcatenateCSVs(paths)
  tempData.filter(element => element.length == 2)
  return tempData
}

const loadCSV = async (path) => {
  const response = await fetch(path);
  const text = await response.text();
  // Assuming CSV content is separated by newlines and commas
  return text.split('\r\n').map(line => line.split(','));
};

// Function to load all CSV files and concatenate their lines
const loadAndConcatenateCSVs = async (filePaths) => {
  const allLines = [];

  for (const path of filePaths) {
    const lines = await loadCSV(path);
    allLines.push(...lines);
  }

  return allLines
}

function parseTimestampWithYearToDict(timestamp) {
  let year = parseInt(timestamp.substring(0, 4), 10);
  let month = parseInt(timestamp.substring(5, 7), 10);
  let day = parseInt(timestamp.substring(8, 10), 10);
  let hour = parseInt(timestamp.substring(11, 13), 10);
  let minute = parseInt(timestamp.substring(14, 16), 10);
  return { 'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute };
}

function zeroPaddedString(timeValue) {
  return timeValue < 10 ? '0' + timeValue : timeValue
}

function getDaysInRange(startDateDict, endDateDict) {
  function createDateString(dict) {
    return `${dict.year}-${String(dict.month).padStart(2, '0')}-${String(dict.day).padStart(2, '0')}`;
  }

  function addDays(date, days) {
    let result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
  }

  let start = new Date(createDateString(startDateDict));
  let end = new Date(createDateString(endDateDict));
  let currentDate = new Date(start);
  let daysInRange = [];

  while (currentDate <= end) {
    daysInRange.push({
      year: currentDate.getFullYear(),
      month: currentDate.getMonth() + 1, // JavaScript months are 0-indexed
      day: currentDate.getDate()
    });
    currentDate = addDays(currentDate, 1);
  }

  return daysInRange;
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
  var kisteremOverride = false
  for (const room in decisions['kisteremOverride']) {
    if (decisions['kisteremOverride'][room]['override']) {
      kisteremOverride = true
    }
  }

  var masterOnDetected = false
  for (var cycle = 1; cycle < 5; cycle++) {
    if (masterOverrides[cycle] == 1) {
      masterOnDetected = true
    }
  }

  allDecisionMessages = []
  var how = masterOnDetected ? 'manuálisan\n' : (decisions['albatros']['reason'] === 'vote' ? 'normál\nüzemmenetben' : (kisteremOverride ? '\njeltovábbítási probléma\nmiatt' : '\ndirektben'))
  var to = decisions['albatros']['decision'] == 0 ? 'ki' : 'be'
  var albatrosMessage = {
    'message': 'Kazánok ' + how + ' ' + to + 'kapcsolva.',
    'timestamp': decisions['albatros']['timestamp']
  }
  allDecisionMessages.push(albatrosMessage)

  var cycleMessages = []
  for (var cycle = 1; cycle < 5; cycle++) {
    var who = ['1-es', '2-es', '3-mas', '4-es'][cycle - 1]
    var how = masterOverrides[cycle] != 0 ? 'manuálisan\n' : (decisions['cycle'][cycle]['reason'] === 'vote' ? 'normál\nüzemmenetben' : (decisions['kisteremOverride'][cycle]['override'] ? '\njeltovábbítási probléma\nmiatt' : '\ndirektben'))
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
    kisteremOverride || masterOnDetected ? (kisteremOverride ? "Jeltovábbítási probléma\nmiatti felülvezérlés." : "Manuális felülvezérlés.") : (externalTempAllow == 1 ?
      (wantHeatingCount == 0 ? "Senki nem kér fűtést." : "Fűtést kér: " + reshapeArray(wantHeatingList, ceil(wantHeatingList.length / 2), 2, null).map(arr => arr.join(', ')).join(',\n') + ".") : "Határérték feletti kinti\nhőmérséklet miatt nincs fűtés."),
    externalTempAllow == 1 && wantHeatingCount > 0 ?
      (problematicCount == 0 ? "Nincs problémás helyiség." : "Eltérések: " + reshapeArray(problematicList, ceil(problematicList.length / 2), 2, null).map(arr => arr.join(', ')).join(',\n') + " (" + round(100 * problematicCount / noOfControlledRooms) + "%).") : "",
    "Utolsó esemény:\n" + (parseTimestampToList(latestMessage['timestamp'])[2] < 10 ? "0" : "") + parseTimestampToList(latestMessage['timestamp'])[2] + ":" + (parseTimestampToList(latestMessage['timestamp'])[3] < 10 ? "0" : "") + parseTimestampToList(latestMessage['timestamp'])[3] + " - " + latestMessage['message']
  ].filter(element => element !== '').join('\n\n')

  stroke(0)
  strokeWeight(2)
  var x = width * 0.185
  var y = height * 0.75
  var w = width * 0.275
  var h = max((countNewLines(messages) + 1) * width * 0.014, height * 0.375)
  rect(x, y, w, h, width * 0.01)

  fill(0)
  noStroke()
  textSize(width * 0.014)
  text(messages, x, y)
}

function manageToolTip() {
  toolTip.draw()
  toolTip.hide()
}

function drawStateVisualization() {
  problematicCount = 0
  problematicList = []
  wantHeatingCount = 0
  wantHeatingList = []
  setDrawingParameters()
  drawCycles()
  drawPipingAndBoiler()
}

function setDrawingParameters() {
  roomTempMax = 30
  roomTempMin = 10
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
      var roomBuffersNormalized = [map(roomSetting - bufferZones[roomNumber]['lower'], roomTempMin, roomTempMax, 0, 1), map(roomSetting + bufferZones[roomNumber]['upper'], roomTempMin, roomTempMax, 0, 1)]
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

      drawRoom(roomX, roomY, roomBaseSize * 0.3, roomBaseSize * 1.6, roomStatus, roomSetting, roomStatusNormalized, roomSettingNormalized, roomBuffersNormalized, roomStatusColor, roomSettingColor, cycleColor, cycleState, roomName, roomNumber, cycle)
    }

    if (decisions['cycle'][cycle]['reason'] === 'vote') {
      wantHeatingCount += decisions['cycle'][cycle]['decision']
    }
  }
}

function drawRoom(x, y, w, h, roomStatus, roomSetting, roomStatusNormalized, roomSettingNormalized, roomBuffersNormalized, roomStatusColor, roomSettingColor, cycleColor, cycleState, roomName, roomNumber, cycle) {
  fill(1)
  noStroke()
  rect(x, y + h / 2, w, h)

  var roomSummedStatus = roomSetting * externalTempAllow * (masterOverrides[cycle] == -1 ? 0 : 1)

  var lastUpdateInHours, lastUpdateInHoursLimit, roomReachableLocal
  
  roomReachableLocal = true
  if (masterOverrides[cycle] != -1) {
    lastUpdateInHours = minutesSince(roomLastUpdate[roomNumber]) / 60
    lastUpdateInHoursLimit = 12
    roomReachableLocal = roomReachable[roomNumber] == false || lastUpdateInHoursLimit <= lastUpdateInHours ? false : true
    console.log(roomReachableLocal)
  }

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

    if (masterOverrides[cycle] != -1) {
      noStroke()
      fill(appendAlpha(roomSettingColor, 0.25))
      topRect(x, y + h * (1 - roomBuffersNormalized[1]), w * 1.125, h * (roomBuffersNormalized[1] - roomBuffersNormalized[0]))
      fill(roomSettingColor)
      rect(x, y + h * (1 - roomSettingNormalized), w * 1.25, h * 0.0125)
      textSize(width * 0.017)
      textStyle(BOLD)
      text(roomSetting, x - w * 1.2, y + map(roomTempMax - roomSetting + roomTempMin, roomTempMin, roomTempMax, 0, h))
    }

    noStroke()
    fill(1)
    ellipse(x, y + h * (1 - roomStatusNormalized), 1.25 * w / 2.5, 1.25 * w / 2.5)
    topRect(x, y + h * (1 - roomStatusNormalized), 1.8 * w / 6, h * roomStatusNormalized)
    roomReachableLocal ? fill(roomStatusColor) : fill(0.5)
    ellipse(x, y + h * (1 - roomStatusNormalized), w / 2.5, w / 2.5)
    topRect(x, y + h * (1 - roomStatusNormalized), w / 6, h * roomStatusNormalized)
    textSize(width * 0.017)
    textStyle(BOLD)
    text(round(roomStatus), x + w * 1.2, y + map(roomTempMax - roomStatus + roomTempMin, roomTempMin, roomTempMax, 0, h))
    textStyle(NORMAL)
    if (mouseOver(x + w * 1.2, y + map(roomTempMax - roomStatus + roomTempMin, roomTempMin, roomTempMax, 0, h), width * 0.05, height * 0.05)) {
      var lastUpdateHourMinute = roomLastUpdate[roomNumber].slice(-5)
      toolTip.show(roomReachableLocal ? round(roomStatus, 1) + ' °C\n(' + lastUpdateHourMinute + ')' : ('Szenzor nem elérhető!'))
    }
  }

  stroke(cycleColor)
  strokeWeight(pipeThickness / 2)
  line(x - w / 2, y, x + w / 2, y)
  line(x - w / 2, y + h, x + w / 2, y + h)

  noStroke()
  fill(229 / 255, 222 / 255, 202 / 255)
  rect(x, y - h * 0.125, w * 2.5, h * 0.14)
  noStroke()

  var roomMessage = ''
  var roomNameDecoration = ''
  var problematic = false

  if (masterOverrides[cycle] == 0) {
    if (roomSetting == 0 || roomSetting == 1) {
      if (roomSummedStatus != cycleState) {
        problematicCount += 1
        problematic = true
        if (mouseOver(x, y + h / 2, w, h)) {
        }
        roomMessage = (cycleState == 1 ? 'Nem kéri, mégis fűtünk.' : 'Kéri, mégsincs fűtés.')
        roomNameDecoration = (cycleState == 1 ? '🥵' : '🥶')
        problematicList.push(roomName)
      }
    }
    else if (cycleState == 1) {
      if (roomStatus > roomSetting + bufferZones[roomNumber]['upper']) {
        problematicCount += 1
        problematic = true
        roomMessage = roomStatus >= 23 ? 'Meleg van, mégis fűtünk.' : 'Kellemes meleg van.'
        roomNameDecoration = roomStatus >= 23 ? '🥵' : '😊'
        problematicList.push(roomName)
      }
      else if (roomStatus < roomSetting - bufferZones[roomNumber]['lower']) {
        roomMessage = 'Hideg van, fűtünk.'
        roomMessage = roomStatus <= 18 ? (roomStatus <= 16 ? 'Hideg van, fűtünk.' : 'Hideg van, fűtünk.') : 'Kezd jó lenni.'
        roomNameDecoration = roomStatus <= 18 ? (roomStatus <= 16 ? '🥶' : '😑') : '😌'
        wantHeatingList.push(roomName)
      }
      else if (roomSetting - bufferZones[roomNumber]['lower'] <= roomStatus <= roomSetting + bufferZones[roomNumber]['upper']) {
        roomMessage = 'Alsó hiszterézis.'
        roomNameDecoration = '😌'
        wantHeatingList.push(roomName)
      }
    }
    else {
      if (roomStatus < roomSetting - bufferZones[roomNumber]['lower']) {
        problematicCount += 1
        problematic = true
        roomMessage = 'Hideg van, mégsincs fűtés.'
        roomNameDecoration = '🥶'
        problematicList.push(roomName)
      }
      else if (roomStatus > roomSetting + bufferZones[roomNumber]['upper']) {
        roomMessage = 'Meleg van, nem fűtünk.'
        roomNameDecoration = '😊'
      }
      else if (roomSetting - bufferZones[roomNumber]['lower'] <= roomStatus <= roomSetting + bufferZones[roomNumber]['upper']) {
        roomMessage = 'Felső hiszterézis.'
        roomNameDecoration = '😊'
      }
    }
  }
  else {
    if (masterOverrides[cycle] == 1) {
      roomMessage = 'Manuálisan bekapcsolt körön.'
      roomNameDecoration = '😬'
    }
    else if (masterOverrides[cycle] == -1) {
      roomMessage = 'Manuálisan kikapcsolt körön.'
      roomNameDecoration = '😴'
    }
  }
  if (roomReachableLocal == false) {
    roomMessage = 'Szenzor nem elérhető!'
    roomNameDecoration = '😶'
  }

  if (mouseOver(x, y - h * 0.125, w * 2.5, h * 0.14) && roomMessage !== '') {
    toolTip.show(roomMessage)
  }

  fill(0)
  textSize(width * 0.013)
  text(roomName + (roomNameDecoration == '' ? '' : ' ' + roomNameDecoration), x, y - h * 0.125)

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

  var masterOnDetected = false
  for (var cycle = 1; cycle < 5; cycle++) {
    if (masterOverrides[cycle] == 1) {
      masterOnDetected = true
    }
  }

  if (mouseOver(x, y, w, h)) {
    var how = masterOnDetected ? 'manuálisan' : (decisions['albatros']['reason'] === 'vote' ? 'normál\nüzemmenetben' : 'direktben')
    var to = decisions['albatros']['decision'] > 0 ? 'be' : 'ki'
    toolTip.show('Kazánok ' + how + '\n' + to + 'kapcsolva.\n(' + decisions['albatros']['timestamp'] + ')')
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
  if (albatrosStatus == 1) {//DEV
    let wiggleAmount = 0.016
    drawFlame(x * 0.99, 1.16 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.095 * random(1 - wiggleAmount, 1 + wiggleAmount), width * 0.055 * random(1 - wiggleAmount, 1 + wiggleAmount), color(1, 0.5, 0, 0.875), color(1, 1, 0, 0.9), true)
    drawFlame(x * 1.01, 1.16 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.095 * 0.85 * random(1 - wiggleAmount, 1 + wiggleAmount), width * 0.055 * 0.85 * random(1 - wiggleAmount, 1 + wiggleAmount), color(1, 0.5, 0, 0.875), color(1, 1, 0, 0.9), true)
  }
  else {
    let wiggleAmount = 0.035
    for (var n = 0; n < 10; n++) {
      drawFlame(width * 0.5 + map(n, 0, 9, -w / 3.75, w / 3.75), 1.125 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.0195 * random(1 - wiggleAmount, 1 + wiggleAmount), width * 0.01 * random(1 - wiggleAmount, 1 + wiggleAmount), color(128 / 255, 234 / 255, 237 / 255, 0.875), color(47 / 255, 118 / 255, 200 / 255, 0.9), true)
    }
  }

  fill(albatrosStatus, 0, 1 - albatrosStatus)
  fill(1)
  rect(width * 0.5, 1.155 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.005 + width * 0.035, width * 0.005 + width * 0.005)
}

function drawPump(x, y, state, cycle) {
  var w = width * 0.0045;
  var l = width * 0.035;

  var discrepancy = false
  var coolOff = false
  if (unitize(decisions['cycle'][cycle]['decision']) == pumpStatuses[cycle]) {
    if (
      (decisions['cycle'][cycle]['decision'] == 0 && pumpStatuses[cycle] == 1) &&
      day() == parseTimestampToList(decisions['cycle'][cycle]['timestamp'])[1] &&
      hour() == parseTimestampToList(decisions['cycle'][cycle]['timestamp'])[2] &&
      minute() - parseTimestampToList(decisions['cycle'][cycle]['timestamp'])[3] <= 3.5
    ) {
      coolOff = true
    }
  }
  else {
    discrepancy = true
  }

  if (mouseOver(x, y, l * 1.1, l * 1.1)) {
    var who = ['1-es', '2-es', '3-mas', '4-es'][cycle - 1]
    var how, to, timestamp
    if (masterOverrides[cycle] == 0) {
      how = decisions['kisteremOverride'][cycle]['override'] == 1 ? 'jeltovábbítási\nprobléma miatt' : (decisions['cycle'][cycle]['reason'] === 'vote' ? 'normál\nüzemmenetben' : 'direktben')
      to = decisions['cycle'][cycle]['decision'] == 0 ? 'ki' : 'be'
      timestamp = '\n(' + decisions['cycle'][cycle]['timestamp'] + ')'
    }
    else {
      how = 'manuálisan'
      to = masterOverrides[cycle] == -1 ? 'ki' : 'be'
      timestamp = ''
    }
    toolTip.show(
      discrepancy ?
        'Eltérés a kör igénye és a\nszivattyú állapota között.' :
        who + ' kör ' + how + '\n' + to + 'kapcsolva' + (coolOff ? '(fűtővíz lepörgetés)' : '') + '.' + timestamp
    )
  }

  if (discrepancy) {
    noStroke()
    fill(1, 0, 0, 0.25)
    ellipse(x, y, l * 0.75, l * 0.75)
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

function appendAlpha(col, alphaVal) {
  // Extract the RGB components from the color object
  let r = red(col);
  let g = green(col);
  let b = blue(col);

  // Return a new color with the specified alpha value
  return color(r, g, b, alphaVal);
}

function calculateTimeDifferenceInMinutes(dateString1, dateString2) {
  // Parse the date strings into Date objects
  const date1 = new Date(dateString1);
  const date2 = new Date(dateString2);

  // Calculate the difference in milliseconds
  const differenceInMilliseconds = Math.abs(date2 - date1);

  // Convert milliseconds to minutes
  const differenceInMinutes = differenceInMilliseconds / 1000 / 60;

  return differenceInMinutes;
}

function minutesSince(dateString) {
  // Assuming dateString is in 'MM.DD. HH:MM' format
  const [monthDay, time] = dateString.split('. ');
  const [month, day] = monthDay.split('.');
  const [hours, minutes] = time.split(':');

  // Constructing a Date object from the given string
  const year = new Date().getFullYear(); // Assuming current year
  const date = new Date(year, month - 1, day, hours, minutes);

  // Getting current date and time
  const now = new Date();

  // Calculating the difference in minutes
  const diff = (now - date) / (1000 * 60); // Convert milliseconds to minutes

  return Math.max(0, Math.floor(diff)); // Return the difference, rounded down, or 0 if it's a future date
}

function transposeArray(array) {
  return array[0].map((_, colIndex) => array.map(row => row[colIndex]));
}

function minMax(array) {
  return [min(array), max(array)]
}

function unitize(num) {
  return num == 0 ? 0 : abs(num) / abs(num)
}

function reshapeArray(arr, n, m, paddingElement) {
  // Create an empty 2D array
  let result = [];

  for (let row = 0; row < n; row++) {
    // Create a new row
    let newRow = [];

    for (let col = 0; col < m; col++) {
      // Compute the index in the original array
      let index = row * m + col;

      // Check if index is within the bounds of the original array
      if (index < arr.length) {
        newRow.push(arr[index]);
      } else {
        // If paddingElement is null and we're on the last row, break the loop
        if (paddingElement === null && row === n - 1) {
          break;
        }
        newRow.push(paddingElement);
      }
    }

    // Add the completed row to the result
    result.push(newRow);
  }

  return result;
}

function countNewLines(str) {
  return (str.match(/\n/g) || []).length
}