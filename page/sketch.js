var plugInfo
var roomToCycle, cycleToRoom
var configAsTable, configAsDict
var roomNames, bufferZones
var sketchAspectRatio
var toolTip
var dataToPlot
var dataToPlotLocked
var roomToPlotNumber
var cycleToPlotNumber
var noOfControlledRooms
var masterOverrides
var raspiConsole, raspiImage, lastUpdateFromRaspi
var radioCommList = []
let activeDataFiles = []
var formattedDataDir
var baseDataFileList
let loadedData = {}

function preload() {
  raspiImage = loadImage('raspi_logo.png');
}

function setup() {
  let canvas = createCanvas(windowWidth, windowHeight)
  sketchAspectRatio = 1.9
  enforceAspectRatio(sketchAspectRatio)
  canvas.parent('canvas-container')
  noFill()
  noStroke()
  colorMode(RGB, 1)
  strokeCap(PROJECT)
  rectMode(CENTER)
  textAlign(CENTER, CENTER)
  imageMode(CENTER)
  textFont('Consolas')
  toolTip = new ToolTipBox()
  dataToPlot = 'external_temp'
  dataToPlotLocked = false

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

  raspiConsole = []
  lastUpdateFromRaspi = null
  listenToFirebase('console/message', (data) => {
    storeRasPiConsole(data)
  })

  baseDataFileList = [
    "external_temp",
    "gas_flow",
    "gas_stock",
    "heat_flow",
    "heat_stock",
    "room_1_temps",
    "room_2_temps",
    "room_3_temps",
    "room_4_temps",
    "room_5_temps",
    "room_6_temps",
    "room_7_temps",
    "room_8_temps",
    "room_9_temps",
    "room_10_temps"
  ]

  for (const fileName of baseDataFileList) {
    for (const date of getDatesList(20, 0)) {
      addActiveDataFile(date, fileName)
    }
  }

  loadActiveDataFiles()
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
var prevPumpStatuses = pumpStatuses
var roomSettings = { 1: 1, 2: 21, 3: 20, 4: 16, 5: 16, 6: 21, 7: 16, 8: 16, 9: 16, 10: 22, 11: 22 }
var roomStatuses = { 1: 0.5, 2: 25, 3: 12, 4: 16, 5: 20, 6: 22, 7: 24, 8: 14, 9: 15, 10: 17, 11: 20 }
var prevRoomStatuses = roomStatuses
var externalTempAllow = 0
var roomReachable
var roomLastUpdate

function updateState(dataFromFirebase) {
  albatrosStatus = dataFromFirebase['albatrosStatus']
  prevPumpStatuses = pumpStatuses
  pumpStatuses = dataFromFirebase['pumpStatuses']
  roomSettings = dataFromFirebase['roomSettings']
  prevRoomStatuses = roomStatuses
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
    drawDataBox()

    manageToolTip()
    dataToPlot = 'external_temp'
  } catch (error) {
    console.log(error.message)
    console.log(error.stack)
  }
}


function drawRadioWaves() {
  for (var i = radioCommList.length - 1; i >= 0; i--) {
    radioCommList[i].draw()
    if (radioCommList[i].dead) {
      radioCommList.splice(i, 1)
    }
  }
}

//#region Data
function getFormattedDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0'); // months are 0-indexed
  const day = String(date.getDate()).padStart(2, '0');

  return `${year}-${month}-${day}`;
}

function getDatesList(startDaysAgo, endDaysAgo) {
  const datesList = [];
  const today = new Date();

  for (let day = startDaysAgo; day >= endDaysAgo; day--) {
    const date = new Date(today);
    date.setDate(date.getDate() - day);
    datesList.push(getFormattedDate(date));
  }

  return datesList;
}

function generateFormattedDataFileURL(date, dataFileName) {
  formattedDataDir = "https://raw.githubusercontent.com/markusbenjamin/kazankontroll-dashboard/main/data/formatted/"
  return formattedDataDir + "/" + date + "/" + dataFileName + ".csv"
}

function loadActiveDataFiles() {
  for (file of activeDataFiles) {
    checkForNewData(file)
  }
}

setInterval(checkFiles, 5 * 60 * 1000);

function checkFiles() {
  activeDataFiles.forEach(file => {
    checkForNewData(file);
  });
}

function checkForNewData(file) {
  fetch(file.url)
    .then(response => response.text())
    .then(data => {
      parseData(data, file.date, file.name)
      file.lastChecked = new Date().getTime();
    })
    .catch(error => console.error('Error fetching data for file:', file.url, error));
}

// Function to dynamically add a new file to the list
function addActiveDataFile(dataDate, fileName) {
  activeDataFiles.push({ url: generateFormattedDataFileURL(dataDate, fileName), lastChecked: null, date: dataDate, name: fileName });
}

// Function to remove a file from the list
function removeActiveDataFile(dataDate = null, fileName = null) {
  activeDataFiles.forEach(file => {
    let shouldDelete = false;

    // Check conditions and mark for deletion
    if (dataDate && fileName) {
      shouldDelete = file.date === dataDate && file.name === fileName;
    } else if (dataDate) {
      shouldDelete = file.date === dataDate;
    } else if (fileName) {
      shouldDelete = file.name === fileName;
    }

    // Delete data if marked
    if (shouldDelete) {
      deleteData(file.date, file.name);
    }
  });

  // Now filter the activeDataFiles
  activeDataFiles = activeDataFiles.filter(file => {
    if (dataDate && fileName) {
      return !(file.date === dataDate && file.name === fileName);
    } else if (dataDate) {
      return file.date !== dataDate;
    } else if (fileName) {
      return file.name !== fileName;
    }
    return true;
  });
}

function deleteData(date, filename) {
  if (loadedData[date] && loadedData[date][filename]) {
    delete loadedData[date][filename];

    // Optional: Clean up the date key if it's empty
    if (Object.keys(loadedData[date]).length === 0) {
      delete loadedData[date];
    }
  }
}

function parseCSVToTable(csvData) {
  let table = new p5.Table();

  // Split the CSV data into rows
  let rows = csvData.split('\n');

  // Determine the number of columns from the first row
  let numberOfColumns = rows[0].split(',').length;

  // Add columns to the table
  for (let i = 0; i < numberOfColumns; i++) {
    table.addColumn('column' + i);
  }

  // Add the data to the table
  rows.forEach(row => {
    let cells = row.split(',');
    let tableRow = table.addRow();
    cells.forEach((cell, index) => {
      let cleanedCell = cell.trim();

      // Replace 'n' with null, convert other values to float, and check for NaN
      let value;
      if (cleanedCell === 'n') {
        value = null;
      } else {
        let parsedValue = parseFloat(cleanedCell);
        value = isNaN(parsedValue) ? null : parsedValue;
      }

      tableRow.set('column' + index, value); // Use 'set' to accommodate null values
    });
  });

  return table;
}

function parseData(data, date, filename) {
  let parsedData = parseCSVToTable(data);

  // Create the date key if it doesn't exist
  if (!loadedData[date]) {
    loadedData[date] = {};
  }

  // Add the parsed data under the specific date and filename
  loadedData[date][filename] = parsedData;
}


function drawDataBox() {
  var dataBoxX = width * 0.17
  var dataBoxY = height * 0.725
  var dataBoxW = width * 0.33
  var dataBoxH = height * 0.4725

  switch (dataToPlot) {
    case 'gas_flow':
      drawPlot(
        loadedData[getDatesList(0, 0)]['gas_flow'].getArray(), 0, 1,
        dataBoxX, dataBoxY, dataBoxW, dataBoxH,
        {
          background: true,
          strokeCol: color(0.5, 0, 1),
          strokeWeight: 3,
          plotLabel: 'Mai gázfogyás (m³)',
          joined: true,
          paddingV: 0.25,
          paddingH: 0.15,
          vOffset: 0.0125,
          hOffset: 0.01,
          xRangeExtend: [0, 0],
          yRangeExtend: [0, 0.05],
          yRange: [0, 0.35],
          ticks: [
            transposeArray([
              range(0 * 60, 24 * 60, 120),
              range(0, 24, 2)
            ]),
            transposeArray([
              range(0, 0.4, 0.2),
              range(0, 0.4, 0.2)
            ])
          ],
          gridLines: [
            range(0, 24 * 60, 60),
            range(0, 0.4, 0.1)
          ]
        }
      )
      break;
    case 'room_temp_na':
      drawPlot(
        [[0, 0], [1, 1]], 0, 1,
        dataBoxX, dataBoxY, dataBoxW, dataBoxH,
        {
          strokeCol: color(1, 0),
          message: 'Nem érhető el hőmérsékleti adat.'
        }
      )
      break;
    case 'room_temp':
      var minTemp = min([
        minNum(transposeArray(loadedData[getDatesList(0, 0)]['room_' + str(roomToPlotNumber) + '_temps'].getArray())[1]),
        minNum(transposeArray(loadedData[getDatesList(0, 0)]['room_' + str(roomToPlotNumber) + '_temps'].getArray())[2])
      ])
      var maxTemp = max([
        maxNum(transposeArray(loadedData[getDatesList(0, 0)]['room_' + str(roomToPlotNumber) + '_temps'].getArray())[1]),
        maxNum(transposeArray(loadedData[getDatesList(0, 0)]['room_' + str(roomToPlotNumber) + '_temps'].getArray())[2])
      ])
      drawPlot(
        loadedData[getDatesList(0, 0)]['room_' + str(roomToPlotNumber) + '_temps'].getArray(), 0, 2,
        dataBoxX, dataBoxY, dataBoxW, dataBoxH,
        {
          background: true,
          strokeCol: color(1, 0, 0),
          strokeWeight: 3,
          joined: true,
          points: false,
          curved: false,
          paddingV: 0.25,
          paddingH: 0.13,
          vOffset: 0.0125,
          hOffset: 0.01,
          xRangeExtend: [0, 0],
          yRangeExtend: [-1, 1],
          yRange: [minTemp, maxTemp]
        }
      )
      drawPlot(
        loadedData[getDatesList(0, 0)]['room_' + str(roomToPlotNumber) + '_temps'].getArray(), 0, 1,
        dataBoxX, dataBoxY, dataBoxW, dataBoxH,
        {
          background: false,
          strokeCol: color(0.5, 0, 1),
          strokeWeight: 3,
          plotLabel: 'Mai hőmérsékleti görbe: ' + roomToPlotName,
          joined: false,
          points: true,
          paddingV: 0.25,
          paddingH: 0.13,
          vOffset: 0.0125,
          hOffset: 0.01,
          xRangeExtend: [0, 0],
          yRangeExtend: [-1, 1],
          yRange: [minTemp, maxTemp],
          ticks: [
            transposeArray([
              range(0 * 60, 24 * 60, 120),
              range(0, 24, 2)
            ]),
            transposeArray([
              range(10, 30, 1),
              range(10, 30, 1)
            ])
          ],
          gridLines: [
            range(0, 24 * 60, 60),
            range(10, 30, 1)
          ]
        }
      )
      break;
    default:
      drawPlot(
        loadedData[getDatesList(0, 0)]['external_temp'].getArray(), 0, 1,
        dataBoxX, dataBoxY, dataBoxW, dataBoxH,
        {
          strokeCol: color(0.5, 0, 1),
          strokeWeight: 3,
          plotLabel: 'Mai külső hőmérséklet',
          paddingV: 0.25,
          paddingH: 0.13,
          vOffset: 0.0125,
          hOffset: 0.01,
          xRangeExtend: [0, 0],
          yRangeExtend: [-1, 1],
          ticks: [
            transposeArray([
              range(0 * 60, 24 * 60, 120),
              range(0, 24, 2)
            ]),
            transposeArray([
              range(-20, 30, 2),
              range(-20, 30, 2)
            ])
          ],
          gridLines: [
            range(0, 24 * 60, 60),
            range(-20, 30, 1)
          ]
        }
      )
  }

}

function drawPlot(data, xCol, yCol, x, y, w, h, userOptions) {
  var defaultOptions = {
    boundingCol: color(0.75),
    boundingWeight: 1,
    background: true,
    strokeCol: color(0),
    strokeWeight: 2,
    joined: true,
    points: false,
    dottedEnd: true,
    curved: true,
    axes: [true, true, false],
    paddingH: 0.1,
    paddingV: 0.1,
    hOffset: 0,
    vOffset: 0,
    xRangeExtend: [0, 0],
    yRangeExtend: [0, 0],
    xRange: [minNum(transposeArray(data)[xCol]), maxNum(transposeArray(data)[xCol])],
    yRange: [minNum(transposeArray(data)[yCol]), maxNum(transposeArray(data)[yCol])],
    axesOriginXY: [true, true], //set to true for axis origin at minimum value, pass value as argument for override
    plotLabel: '',
    ticks: [false, false],
    gridLines: [false, false],
    message: null
  }

  options = { ...defaultOptions, ...userOptions };

  stroke(options['boundingCol'])
  strokeWeight(options['boundingWeight'])

  if (options['background']) {
    fill(1)
    rect(x, y, w, h)
    noFill()
  }

  if (options['message'] != null) {
    noStroke()
    fill(0)
    textSize(width * 0.015)
    text(wrapLine(options['message'], w * 0.875), x, y)
    noFill()
  }
  else {
    function x2h(xVal) {
      return map(xVal, options['xRange'][0] + options['xRangeExtend'][0], options['xRange'][1] + options['xRangeExtend'][1], x - w / 2 + w * options['hOffset'] + w * options['paddingH'] / 2, x + w / 2 + w * options['hOffset'] - w * options['paddingH'] / 2)
    }

    function y2v(yVal) {
      return map(yVal, options['yRange'][0] + options['yRangeExtend'][0], options['yRange'][1] + options['yRangeExtend'][1], y + h / 2 + h * options['vOffset'] - h * options['paddingV'] / 2, y - h / 2 + h * options['vOffset'] + h * options['paddingV'] / 2)
    }

    var hRange = [
      x2h(options['xRange'][0] + options['xRangeExtend'][0]),
      x2h(options['xRange'][1] + options['xRangeExtend'][1])
    ]
    var vRange = [
      y2v(options['yRange'][0] + options['yRangeExtend'][0]),
      y2v(options['yRange'][1] + options['yRangeExtend'][1])
    ]

    var axesOriginHV = [
      options['axesOriginXY'][0] == true ? x2h(options['xRange'][0] + options['xRangeExtend'][0]) : x2h(options['axesOriginXY'][0]),
      options['axesOriginXY'][1] == true ? y2v(options['yRange'][0] + options['yRangeExtend'][0]) : y2v(options['axesOriginXY'][1])
    ]

    stroke(0)
    strokeWeight(2)
    if (options['axes'][0]) {
      line(hRange[0], axesOriginHV[1], hRange[1], axesOriginHV[1])
    }
    if (options['axes'][1]) {
      line(axesOriginHV[0], vRange[0], axesOriginHV[0], vRange[1])
    }
    noStroke()

    if (options['ticks'][0] != false) {
      for (const tick of options['ticks'][0]) {
        if (hRange[0] <= x2h(tick[0]) && hRange[1] * 1.01 >= x2h(tick[0])) {
          stroke(0)
          line(x2h(tick[0]), axesOriginHV[1] - 2.5, x2h(tick[0]), axesOriginHV[1] + 2.5)
          noStroke()
          fill(0)
          textSize(width * 0.012)
          text(str(tick[1]), x2h(tick[0]), axesOriginHV[1] + 15)
          noFill()
        }
      }
    }
    if (options['ticks'][1] != false) {
      for (const tick of options['ticks'][1]) {
        if (vRange[0] >= y2v(tick[0]) && vRange[1] * 0.99 <= y2v(tick[0])) {
          stroke(0)
          line(axesOriginHV[0] - 2.5, y2v(tick[0]), axesOriginHV[0] + 2.5, y2v(tick[0]))
          noStroke()
          fill(0)
          textSize(width * 0.012)
          text(str(tick[1]), axesOriginHV[0] - 20, y2v(tick[0]))
          noFill()
        }
      }
    }

    if (options['gridLines'][0] != false) {
      for (const gridLine of options['gridLines'][0]) {
        if (hRange[0] <= x2h(gridLine) && hRange[1] * 1.01 >= x2h(gridLine)) {
          stroke(0, 0.25)
          strokeWeight(1)
          line(x2h(gridLine), vRange[0], x2h(gridLine), vRange[1])
          noStroke()
        }
      }
    }
    if (options['gridLines'][1] != false) {
      for (const gridLine of options['gridLines'][1]) {
        if (vRange[0] >= y2v(gridLine) && vRange[1] * 0.99 <= y2v(gridLine)) {
          stroke(0, 0.25)
          strokeWeight(1)
          line(hRange[0], y2v(gridLine), hRange[1], y2v(gridLine))
          noStroke()
        }
      }
    }

    noStroke()
    fill(0)
    textSize(width * 0.013)
    textAlign(CENTER, CENTER)
    if (options['plotLabel'] != '') {
      text(options['plotLabel'], x, y - h * 0.45)
    }
    noFill()
    textAlign(CENTER, CENTER)

    stroke(options['strokeCol'])
    strokeWeight(options['strokeWeight'])

    if (options['joined']) {
      beginShape()
    }

    var minutesSinceMidnight = round(hour() * 60 + minute(), 5)

    for (const point of data) {
      if (point[yCol] != null) {
        var pointX = x2h(point[xCol])
        var pointY = y2v(point[yCol])
        if (point[xCol] <= minutesSinceMidnight) {
          if (options['joined']) {
            options['curved'] ? curveVertex(pointX, pointY) : vertex(pointX, pointY)
          }
          if (options['points']) {
            ellipse(pointX, pointY, options['strokeWeight'] / 2, options['strokeWeight'] / 2)
          }
        }
      }
    }
    if (options['joined']) {
      endShape()
    }
    if (options['dottedEnd'] && options['points'] == false) {
      fill(options['strokeCol'])
      var breather = map(sin(map(round(millis()) % 1500, 0, 1500, 0, TWO_PI)), -1, 1, 1, 1.25)
      var lastPos = findClosest(transposeArray(data)[xCol], minutesSinceMidnight)
      ellipse(
        x2h(transposeArray(data)[xCol][lastPos]),
        y2v(transposeArray(data)[yCol][lastPos]),
        5 * breather,
        5 * breather
      )
      noFill()
    }
  }
}
//#endregion

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
  var how = masterOnDetected ? 'manuálisan' : (decisions['albatros']['reason'] === 'vote' ? 'normál üzemmenetben' : (kisteremOverride ? 'jeltovábbítási probléma miatt' : 'direktben'))
  var to = decisions['albatros']['decision'] == 0 ? 'ki' : 'be'
  var albatrosMessage = {
    'message': 'Kazánok ' + how + ' ' + to + 'kapcsolva.',
    'timestamp': decisions['albatros']['timestamp']
  }
  allDecisionMessages.push(albatrosMessage)

  var cycleMessages = []
  for (var cycle = 1; cycle < 5; cycle++) {
    var who = ['1-es', '2-es', '3-mas', '4-es'][cycle - 1]
    var how = masterOverrides[cycle] != 0 ? 'manuálisan' : (decisions['cycle'][cycle]['reason'] === 'vote' ? 'normál üzemmenetben' : (decisions['kisteremOverride'][cycle]['override'] ? 'jeltovábbítási probléma miatt' : 'direktben'))
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
    'message': 'Külső hőmérséklet határ ' + aboveOrBelow + ', fűtés ' + onOrOff + 'kapcsolva.',
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

  var lastEventTimestamp = (parseTimestampToList(latestMessage['timestamp'])[2] < 10 ? "0" : "") + parseTimestampToList(latestMessage['timestamp'])[2] + ":" + (parseTimestampToList(latestMessage['timestamp'])[3] < 10 ? "0" : "") + parseTimestampToList(latestMessage['timestamp'])[3]

  var x = width * 0.0975
  var y = height * 0.317
  var w = width * 0.18
  var h = height * 0.25
  var fontSize = width * 0.014

  var rasPiReachable = checkRaspiConnection(1, 10)

  //var messagesPre1 = [
  //  kisteremOverride || masterOnDetected ? (kisteremOverride ? "Jeltovábbítási probléma miatti felülvezérlés." : "Manuális felülvezérlés.") : (externalTempAllow == 1 ?
  //    (wantHeatingCount == 0 ? "Senki nem kér fűtést." : "Fűtést kér: " + wantHeatingList.join(', ')) : "Határérték feletti kinti hőmérséklet miatt nincs fűtés.")//,
  //  //externalTempAllow == 1 && wantHeatingCount > 0 ?
  //  //  (problematicCount == 0 ? "Nincs problémás helyiség." : "Eltérések: " + problematicList.join(', ') + " (" + round(100 * problematicCount / noOfControlledRooms) + "%).") : "",
  //  //"Utolsó esemény: " + latestMessage['message'].substring(0, latestMessage['message'].length - 1) + " (" + lastEventTimestamp + ")."
  //].filter(element => element !== '')
  //
  //var messagesPre2 = []
  //for (const line of messagesPre1) {
  //  messagesPre2.push(wrapLine(line, w * 0.8))
  //}
  //
  //var messages = messagesPre2.join('\n\n')

  var message = wrapLine(
    rasPiReachable ?
    (
      masterOnDetected == 0 ?
      (
        wantHeatingCount == 0 ? "Senki nem kér fűtést." : "Fűtést kér: " + wantHeatingList.join(', ')
        ) : "Manuális felülvezérlés."
    ) : "Nem éri el a vezérlés az internetet!",
    w * 0.8
  )

  h = max((countNewLines(message) + 1) * fontSize, h)
  stroke(0)
  strokeWeight(2)
  fill(1)
  rect(x, y, w, h, width * 0.01)

  fill(0)
  noStroke()
  textSize(fontSize)
  text(message, x + width * 0.005, y)
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
  drawGasMeterAndPiping()
  drawCycles()
  drawPipingAndBoiler()
  drawRasPiWiring()
  drawRasPi()
  drawRadioWaves()
}

function setDrawingParameters() {
  roomTempMax = 25
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
    roomNumAddition = cycle == 3 ? 1.25 : 0

    var cycleState = pumpStatuses[cycle] * albatrosStatus * externalTempAllow
    var cycleColor = color(cycleState, 0, 1 - cycleState)

    stroke(cycleColor)
    strokeWeight(pipeThickness)
    line(width * 0.5, height * cycleYPos[cycle], width * (0.5 + cycleXDir[cycle] * map(cycleToRoom[cycle].length - 1 + roomXPositionOffset, 0, cycleToRoom[cycle].length + roomNumAddition, 0.1, cyclePipeLength)), height * cycleYPos[cycle])
    stroke(albatrosStatus, 0, 1 - albatrosStatus)
    line(width * 0.5, height * cycleYPos[cycle], width * (0.5 + cycleXDir[cycle] * pumpXPositionOffset), height * cycleYPos[cycle])
    drawPump(width * (0.5 + cycleXDir[cycle] * pumpXPositionOffset), height * cycleYPos[cycle], pumpStatuses[cycle], cycle)

    for (var roomOnCycle = 0; roomOnCycle < cycleToRoom[cycle].length; roomOnCycle++) {
      var roomNumber = cycleToRoom[cycle][roomOnCycle]
      var roomX = width * (0.5 + cycleXDir[cycle] * map(roomOnCycle + roomXPositionOffset, 0, cycleToRoom[cycle].length + roomNumAddition, 0.1, cyclePipeLength))
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
    for (var temp = roomTempMin + 0.5; temp <= roomTempMax - 0.5; temp += 0.5) {
      if (temp % 1 == 0) {
        strokeWeight(2)
        stroke(0, 0.45)
        line(x - w / 2, y + map(temp, roomTempMin, roomTempMax, 0, h), x - w * 0.1, y + map(temp, roomTempMin, roomTempMax, 0, h))
        noStroke()
        fill(0, 0.65)
        textSize(width * 0.008)
        text(roomTempMax - temp + roomTempMin, x + w / 4, y + map(temp, roomTempMin, roomTempMax, 0, h))
      }
      else {
        strokeWeight(1)
        stroke(0, 0.5)
        line(x - w / 2, y + map(temp, roomTempMin, roomTempMax, 0, h), x - w * 0.2, y + map(temp, roomTempMin, roomTempMax, 0, h))
        noStroke()
        fill(0, 0.5)
        textSize(width * 0.0075)
        //text(roomTempMax - temp + roomTempMin, x + w / 4, y + map(temp, roomTempMin, roomTempMax, 0, h))
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
      toolTip.show(roomReachableLocal ? round(roomStatus, 1) + ' °C\n(' + lastUpdateHourMinute + ')' : ('Szenzor nem elérhető!'), color(1), color(0), color(0), 4, width * 0.0125, CENTER)
    }

    if (prevRoomStatuses[roomNumber] != roomStatus) {
      var label = 'room' + roomNumber
      var labelExists = false
      for (const radioComm of radioCommList) {
        if (label === radioComm.label) {
          labelExists = true
        }
      }
      if (labelExists == false) {
        radioCommList.push(new RadioCommunication(x + w * 1.2, y + map(roomTempMax - roomStatus + roomTempMin, roomTempMin, roomTempMax, 0, h), raspiX, raspiY, 30, label))
        prevRoomStatuses[roomNumber] = roomStatus
      }
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
      else {
        if (roomSetting == 1) {
          wantHeatingList.push(roomName)
          roomMessage = 'Fűtünk.'
          roomNameDecoration = '😌'
        }
        else {
          roomMessage = 'Nem kér fűtést.'
          roomNameDecoration = '😊'
        }
      }
    }
    else if (cycleState == 1) {
      if (roomStatus > roomSetting + bufferZones[roomNumber]['upper']) {
        roomMessage = (23 <= roomStatus || 3 <= roomStatus - roomSetting + bufferZones[roomNumber]['upper']) ? (roomStatus >= 23 ? 'Meleg van, mégis fűtünk.' : 'Nem kéne, mégis fűtünk.') : 'Nem kéne, mégis fűtünk.'
        roomNameDecoration = (23 <= roomStatus || 3 <= roomStatus - roomSetting + bufferZones[roomNumber]['upper']) ? (roomStatus >= 23 ? '🥵' : '😕') : '😕'
        if (23 <= roomStatus || 3 <= roomStatus - roomSetting + bufferZones[roomNumber]['upper']) {
          problematicCount += 1
          problematic = true
          problematicList.push(roomName)
        }
      }
      else if (roomStatus < roomSetting - bufferZones[roomNumber]['lower']) {
        roomMessage = roomStatus <= 18 ? (roomStatus <= 16 ? 'Hideg van.' : 'Hideg van.') : 'Kezd jó lenni.'
        roomNameDecoration = roomStatus <= 18 ? (roomStatus <= 16 ? '🥶' : '😑') : '😌'
        wantHeatingList.push(roomName)
        if (roomStatus <= min(19, roomSetting)) {
          problematicList.push(roomName)
          problematicCount += 1
          problematic = true
        }
      }
      else if (roomSetting - bufferZones[roomNumber]['lower'] <= roomStatus <= roomSetting + bufferZones[roomNumber]['upper']) {
        roomMessage = 'Alsó hiszterézis.'
        roomNameDecoration = '😌'
        wantHeatingList.push(roomName)
      }
    }
    else {
      if (roomStatus < roomSetting - bufferZones[roomNumber]['lower']) {
        roomMessage = 'Hideg van, mégsincs fűtés.'
        roomNameDecoration = '🥶'
      }
      else if (roomStatus > roomSetting + bufferZones[roomNumber]['upper']) {
        roomMessage = 'Nem kér fűtést.'
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
    toolTip.show(roomMessage, color(1), color(0), color(0), 4, width * 0.0125, CENTER)
    var roomTempData = loadedData[getDatesList(0, 0)]['room_' + str(roomNumber) + '_temps'].getArray()
    var roomTempDataLoaded = loadedData[getDatesList(0, 0)]['room_' + str(roomNumber) + '_temps'].getArray() != undefined
    var roomTempDataContainsNumbers = roomTempDataLoaded ? containsNumber(transposeArray(roomTempData)[1]) : false
    if (roomNumber != 8 && roomTempDataLoaded && roomTempDataContainsNumbers) {
      dataToPlot = 'room_temp'
      roomToPlotNumber = roomNumber
      roomToPlotName = roomName
    }
    else {
      dataToPlot = 'room_temp_na'
      roomToPlotNumber = roomNumber
      roomToPlotName = roomName
    }
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

function storeRasPiConsole(line) {
  if (50 < raspiConsole.length) {
    raspiConsole.splice(0, 1)
  }
  raspiConsole.push(line)
  lastUpdateFromRaspi = new Date().getTime()
}

function drawRasPiWiring() {
  let x1 = 0
  let x2 = 0
  let cx1 = 0
  let cx2 = 0
  if (albatrosStatus == 1) {
    x1 = width * 0.49, y1 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.2
    x2 = width * 0.5, y2 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.525
    cx1 = width * 0.46, cy1 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.21
    cx2 = width * 0.46, cy2 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.625
  }
  else {
    x1 = width * 0.46, y1 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.25
    x2 = width * 0.5, y2 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.525
    cx1 = width * 0.475, cy1 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.21
    cx2 = width * 0.46, cy2 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.625
  }

  noFill();

  stroke(0.9);
  strokeWeight(width * 0.0035)
  bezier(x1, y1, cx1, cy1, cx2, cy2, x2, y2);
  stroke(252 / 255, 178 / 255, 40 / 255);
  strokeWeight(width * 0.003)
  bezier(x1, y1, cx1, cy1, cx2, cy2, x2, y2);
  if (albatrosStatus == 0) {
    noStroke()
    fill(0.5)
    tiltedRect(x1 * 0.98, y1 * 1.02, width * 0.005, width * 0.001, TWO_PI * (-0.058))
    fill(0)
    tiltedRect(x1 * 0.99, y1 * 1.01, width * 0.0065, width * 0.0025, TWO_PI * (-0.058))
  }

  x1 = width * 0.5, y1 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.22
  x2 = width * 0.5, y2 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.54
  cx1 = width * 0.47, cy1 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.19
  cx2 = width * 0.46, cy2 = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.525

  noFill()
  stroke(0.9);
  strokeWeight(width * 0.0035)
  bezier(x1, y1, cx1, cy1, cx2, cy2, x2, y2);
  stroke(23 / 255, 255 / 255, 236 / 255)
  strokeWeight(width * 0.003)
  bezier(x1, y1, cx1, cy1, cx2, cy2, x2, y2)

  stroke(0.5)
  strokeWeight(1)
  fill(0.95, 1, 1)
  rect(width * 0.5, 1.195 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.025, height * 0.026)
}

function checkRaspiConnection(time1, time2) {
  var timesSinceRoomLastUpdate = roomLastUpdate.map(updateTime => {
    const updateTimeString = `${year}.${updateTime.replace(' ', 'T')}:00`;
    // Parse the date-time string to a Date object and get time in milliseconds
    var updateTimeUnixEpoch = new Date(updateTimeUnixEpoch).getTime();
    var now = new Date().getTime()
    var elapsedTime = now - updateTimeUnixEpoch
    return elapsedTime
  });
  var now = new Date().getTime()
  if (
    now - lastUpdateFromRaspi > time1 * 60 * 1000 ||
    minNum(timesSinceRoomLastUpdate) > time2 * 60 * 1000
  ) {
    return false
  }
  else {
    return true
  }
}

var raspiX, raspiY

function drawRasPi() {
  var rasPiReachable = checkRaspiConnection(1, 10)

  raspiX = width * 0.5
  raspiY = height * (cycleYPos[1] + cycleYPos[2]) / 2 * 1.585
  var x = raspiX
  var y = raspiY

  var w = width * 0.025
  var h = width * 0.035

  fill(0)
  noStroke()
  rect(x - w / 2, y - h / 4, w * 0.175, h * 0.3)

  var breathFreq = 2500
  fill(65 / 255, 255 / 255, 113 / 255)
  if (rasPiReachable == false) {
    fill(0.7, 0.7, 0.7)
    breathFreq = 250
  }
  strokeWeight(1)
  stroke(0)
  rect(x, y, w, h)
  var breather = map(sin(map(round(millis()) % breathFreq, 0, breathFreq, 0, TWO_PI)), -1, 1, 0.785, 0.815)
  image(raspiImage, x, y * 1.005, w * breather, w * breather);

  if (mouseOver(x, y, w, h)) {
    if (rasPiReachable) {
      toolTip.show(raspiConsole.slice(max(raspiConsole.length - 40, 0), raspiConsole.length).map(element => element.replace(/[\n]/g, '')).map(line => wrapLine(line, width * 0.7)).join("\n"), color(0), color(0), color(1), 1, width * 0.0075, LEFT)
    }
    else {
      toolTip.show(
        'Nem éri el a vezérlés az internetet!',
        color(1), color(0), color(0), 4,
        width * 0.012, LEFT
      )
    }
  }
}

function drawGasMeterAndPiping() {
  if (loadedData[getDatesList(0, 0)[0]]['gas_stock'] != undefined && 1 < loadedData[getDatesList(0, 0)[0]]['gas_stock'].getArray().length) {
    var x = width * 0.0975
    var y = height * 0.1
    var w = width * 0.07
    var h = w * 2 / 3

    stroke(0.4)
    strokeWeight(pipeThickness * 0.65)
    var pipeDown = width * 0.4925
    var pipeRight = height * 0.035
    line(0, pipeRight, x - w * 0.25, pipeRight)
    line(x - w * 0.25, pipeRight, x - w * 0.25, y)
    line(x + w * 0.25, pipeRight, x + w * 0.25, y)
    line(x + w * 0.25, pipeRight, pipeDown, pipeRight)
    line(pipeDown, pipeRight, pipeDown, height * 0.35)
    strokeWeight(pipeThickness * 1.25)
    stroke(0.65)
    line(x - w * 0.25, pipeRight * 1.55, x - w * 0.25, y)
    line(x + w * 0.25, pipeRight * 1.55, x + w * 0.25, y)

    noStroke()
    fill(0.65)
    rect(x, y, w, h, 10)
    fill(0.9)
    stroke(0)
    strokeWeight(1)
    rect(x, y, w * 0.5, h * 0.45, 5)
    fill(0)
    noStroke()
    textSize(width * 0.015)
    textAlign(CENTER, CENTER)
    var burntVolume = round(maxNum(transposeArray(loadedData[getDatesList(0, 0)[0]]['gas_stock'].getArray())[1]))
    text(str(burntVolume), x, y)
    textAlign(CENTER, CENTER)

    var energyContent = round(burntVolume * 1000 * 34 / 3600)
    var price = burntVolume * 11 * 35 + burntVolume * 30

    var message = [
      'Ma elégett gáz: ' + str(burntVolume) + ' m³',
      'Energiatartalom: ' + str(energyContent) + ' kWh',
      'Becsült ár: ' + str(price) + ' Ft'
    ]

    if (mouseOver(x, y, w * 1.2, h * 1.2)) {
      toolTip.show(
        message.join('\n'),
        color(1), color(0), color(0), 4,
        width * 0.013, LEFT
      )
      dataToPlot = 'gas_flow'
    }
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

  var gasDataAvailable = loadedData[getDatesList(0, 0)[0]]['gas_stock'] != undefined && 1 < loadedData[getDatesList(0, 0)[0]]['gas_stock'].getArray().length
  var heatDataAvailable = transposeArray(loadedData[getDatesList(0, 0)[0]]['heat_stock'].getArray())[1] != undefined
  var totalDeliveredHeat = 0
  var efficiency = 0
  if (gasDataAvailable && heatDataAvailable) {
    var burntVolume = round(maxNum(transposeArray(loadedData[getDatesList(0, 0)[0]]['gas_stock'].getArray())[1]))
    var energyContent = round(burntVolume * 1000 * 34 / 3600)
    totalDeliveredHeat = 0
    for (var cycle = 1; cycle < 5; cycle++) {
      var currentReadout = maxNum(transposeArray(loadedData[getDatesList(0, 0)[0]]['heat_stock'].getArray())[cycle])
      var dailyStart = minNum(transposeArray(loadedData[getDatesList(0, 0)[0]]['heat_stock'].getArray())[cycle])
      totalDeliveredHeat += round(currentReadout - dailyStart)
    }
    efficiency = round(100 * totalDeliveredHeat / energyContent)
  }


  if (mouseOver(x, y, w, h)) {
    var how = masterOnDetected ? 'manuálisan' : (decisions['albatros']['reason'] === 'vote' ? 'normál\nüzemmenetben' : 'direktben')
    var to = decisions['albatros']['decision'] > 0 ? 'be' : 'ki'
    var performanceInfo = 'Mai hőmennyiség: ' + str(totalDeliveredHeat) + ' kWh\nHatékonyság: ' + str(efficiency) + '%'
    toolTip.show('Kazánok ' + how + '\n' + to + 'kapcsolva.\n(' + decisions['albatros']['timestamp'] + ')' + (gasDataAvailable && heatDataAvailable ? '\n\n' + performanceInfo : ''), color(1), color(0), color(0), 4, width * 0.0125, CENTER)
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

  fill(1)
  rect(width * 0.5, 1.155 * height * (cycleYPos[1] + cycleYPos[2]) / 2, width * 0.005 + width * 0.035, width * 0.005 + width * 0.005)
}

function drawPump(x, y, state, cycle) {
  var w = width * 0.0045;
  var l = width * 0.035;
  var heatmeterX = width * 0.5 - Math.sign(width * 0.5 - x) * width * 0.032
  var heatmeterY = y + height * 0.1125
  var heatmeterW = l * 0.85
  var heatmeterH = w * 2.75
  var drawHeatmeter = transposeArray(loadedData[getDatesList(0, 0)[0]]['heat_stock'].getArray())[1] != undefined

  var discrepancy = false
  var coolOff = false
  if (unitize(decisions['cycle'][cycle]['decision']) != pumpStatuses[cycle]) {
    if (millisSince(decisions['cycle'][cycle]['timestamp']) / (60 * 1000) <= 4) {
      coolOff = true
    }
    else {
      discrepancy = true
    }
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
        who + ' kör ' + how + '\n' + to + 'kapcsolva' + (coolOff ? '\n(fűtővíz lepörgetés)' : '') + '.' + timestamp,
      color(1), color(0), color(0), 4,
      width * 0.0125, CENTER
    )
  }

  if (discrepancy) {
    noStroke()
    fill(1, 0, 0, 0.25)
    ellipse(x, y, l * 0.75, l * 0.75)
  }

  //Draw heatmeter wires
  if (drawHeatmeter) {
    var heatmeterProbeX = heatmeterX + (Math.sign(width * 0.5 - x) == 1 ? width * 0.01 : -width * 0.01)
    stroke(0)
    strokeWeight(2.5)
    noFill()
    drawCord(heatmeterX, heatmeterY, heatmeterProbeX, y, -Math.sign(width * 0.5 - x))
    fill(0)
    rect(heatmeterProbeX, y, pipeThickness * 0.5, pipeThickness * 1.75, 2)
  }

  var innerShade = 0
  var outerShade = 0

  if (state == 0) {
    stroke(outerShade)
    strokeWeight(2)
    fill(outerShade)
    rect(x, y, w, l)
    ellipse(x, y + l / 2, width * 0.0165 * 0.6, width * 0.0165 * 0.3)
    ellipse(x, y - l / 2, width * 0.0165 * 0.6, width * 0.0165 * 0.3)
    stroke(innerShade)
    strokeWeight(1)
    fill(innerShade)
    rect(x, y, w * 0.3, l)
    ellipse(x, y + l / 2, width * 0.0165 * 0.6 * 0.5, width * 0.0165 * 0.3 * 0.28)
    ellipse(x, y - l / 2, width * 0.0165 * 0.6 * 0.5, width * 0.0165 * 0.3 * 0.28)
  }
  else {
    stroke(outerShade)
    strokeWeight(2)
    fill(outerShade)
    rect(x, y, l, w)
    ellipse(x + l / 2, y, width * 0.0165 * 0.3, width * 0.0165 * 0.6)
    ellipse(x - l / 2, y, width * 0.0165 * 0.3, width * 0.0165 * 0.6)
    stroke(innerShade)
    strokeWeight(2)
    fill(innerShade)
    rect(x, y, l, w * 0.3)
    ellipse(x + l / 2, y, width * 0.0165 * 0.3 * 0.28, width * 0.0165 * 0.3 * 0.5)
    ellipse(x - l / 2, y, width * 0.0165 * 0.3 * 0.28, width * 0.0165 * 0.3 * 0.5)
  }
  strokeWeight(2)
  stroke(outerShade)
  fill(outerShade)
  ellipse(x, y, width * 0.01, width * 0.01)
  stroke(innerShade)
  fill(innerShade)
  stroke(1)
  fill(1)
  ellipse(x, y, width * 0.01 * 0.25, width * 0.01 * 0.25)

  //Draw heatmeters
  if (drawHeatmeter) {
    stroke(1)
    strokeWeight(2)
    fill(1)
    rect(heatmeterX, heatmeterY, heatmeterW * 1.28, heatmeterH * 1.6, 3)
    stroke(0)
    strokeWeight(1)
    fill(0.9)
    rect(heatmeterX, heatmeterY, heatmeterW, heatmeterH)
    noFill()
    noStroke()
    fill(0)
    textSize(width * 0.012)
    textAlign(RIGHT, CENTER)
    var currentReadout = maxNum(transposeArray(loadedData[getDatesList(0, 0)[0]]['heat_stock'].getArray())[cycle])
    var dailyStart = minNum(transposeArray(loadedData[getDatesList(0, 0)[0]]['heat_stock'].getArray())[cycle])
    var seasonStarts = [2420, 133, 12, 2]
    var dailyHeat = round(currentReadout - dailyStart)
    text(str(dailyHeat), heatmeterX + heatmeterW / 2 * 0.925, heatmeterY + heatmeterH * 0.05)
    textAlign(CENTER, CENTER)

    if (mouseOver(heatmeterX, heatmeterY, heatmeterW * 1.2, heatmeterH * 1.2)) {
      var who = ['1-es', '2-es', '3-mas', '4-es'][cycle - 1]
      var offset = [10115, 10232, 0, 0][cycle - 1]
      toolTip.show(
        who + ' körön leadott hő:\nSzezonban: ' + str(offset + currentReadout - seasonStarts[cycle - 1]) + ' kWh\nMa: ' + str(dailyHeat) + ' kWh',
        color(1), color(0), color(0), 4,
        width * 0.012, LEFT
      )
    }
  }

  if (prevPumpStatuses[cycle] != pumpStatuses[cycle]) {
    var label = 'pump' + cycle
    var labelExists = false
    for (const radioComm of radioCommList) {
      if (label === radioComm.label) {
        labelExists = true
      }
    }
    if (labelExists == false) {
      radioCommList.push(new RadioCommunication(raspiX, raspiY, x, y, 10, label))
      prevPumpStatuses[cycle] = pumpStatuses[cycle]
    }
  }
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

function mousePressed() {
  dataToPlotLocked = !dataToPlotLocked
}

function topRect(x, y, w, h) {
  rectMode(CORNER)
  let adjustedX = x - w / 2;
  let adjustedY = y;
  rect(adjustedX, adjustedY, w, h);
  rectMode(CENTER)
}

function tiltedRect(x, y, w, h, angle) {
  push(); // Save the current drawing state
  translate(x, y); // Move the origin to the rectangle's center
  rotate(angle); // Rotate by the specified angle (in radians)
  rectMode(CENTER); // Draw the rectangle from its center
  rect(0, 0, w, h); // Draw the rectangle
  pop(); // Restore the original drawing state
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

function roundTo(val, round) {
  return Math.round(val / round) * round;
}

function range(start, end, step = 1) {
  let arr = [];
  for (let i = start; i <= end; i += step) {
    arr.push(i);
  }
  return arr;
}

class ToolTipBox {
  constructor() {
    this.text = "";
    this.isVisible = false;
    this.padding = width * 0.0075;
    this.textSize = width * 0.0125;
    this.rounding = 4
    this.hAlign = CENTER;
    this.borderColor = color(0)
    this.fillColor = color(1);
    this.textColor = color(0);
  }

  // Call this function to display the tooltip with the provided text
  show(text, fillColor, borderColor, textColor, rounding, textSize, hAlign) {
    this.text = text
    this.isVisible = true
    this.textSize = textSize
    this.hAlign = hAlign
    this.borderColor = textColor
    this.fillColor = fillColor
    this.borderColor = borderColor
    this.textColor = textColor
    this.rounding = rounding
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
      textAlign(this.hAlign, CENTER)
      let txtWidth = multiLineTextWidth(this.text) + this.padding * 2;
      let txtHeight = 2 * this.padding + 1.2 * this.textSize * (1 + (this.text.match(/\n/g) || []).length);

      // Determine the position of the tooltip so it doesn't hang off the edge
      let posX = mouseX + txtWidth / 2; // Offset from mouse position
      let posY = mouseY + txtHeight / 2;

      // Adjust if it's going out of the canvas
      if (posX + txtWidth / 2 > width) {
        posX = width - txtWidth / 2;
      }
      if (posY + txtHeight / 2 > height) {
        posY = height - txtHeight / 2;
      }

      stroke(this.borderColor);
      strokeWeight(1)
      fill(this.fillColor);
      rect(posX, posY, txtWidth, txtHeight, this.rounding);

      // Draw the tooltip text
      noStroke()
      fill(this.textColor);
      text(this.text, posX + (this.hAlign === CENTER ? 0 : -txtWidth / 2 + this.padding), posY);
      textAlign(CENTER, CENTER)
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
  return millisSince(dateString) / (60 * 1000)
}

function millisSince(dateString) {
  // Assuming dateString is in 'MM.DD. HH:MM' format
  const [monthDay, time] = dateString.split('. ');
  const [month, day] = monthDay.split('.');
  const [hours, minutes] = time.split(':');

  // Constructing a Date object from the given string
  const year = new Date().getFullYear(); // Assuming current year
  const date = new Date(year, month - 1, day, hours, minutes);

  // Getting current date and time
  const now = new Date();

  // Calculating the difference in millis
  return (now - date)
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

function wrapLine(line, w) {
  if (w < multiLineTextWidth(line)) {
    var words = split(line, ' ')
    var wrappedLine = ''
    var wrappingLenght = 0
    for (const word of words) {
      if (wrappingLenght < w * 0.9) {
        wrappedLine += word + ' '
        wrappingLenght += multiLineTextWidth(wrappedLine + word)
      }
      else {
        wrappedLine += '\n' + ('\t'.repeat((line.match(/\t/g) || []).length)) + word + ' '
        wrappingLenght = 0
      }
    }
    return wrappedLine
  }
  else {
    return line
  }
}

function drawCord(x1, y1, x2, y2, swap) {
  let steps = 100;
  let amplitude = 10;
  let frequency = TWO_PI / steps; // Complete one cycle over the path

  beginShape();
  curveVertex(x1, y1); // Start point

  for (let i = 1; i < steps; i++) {
    let x = lerp(x1, x2, i / steps);
    let y = lerp(y1, y2, i / steps);
    let twist = amplitude * sin(i * frequency);

    if (i === 1 || i === steps - 1) {
      twist = 0; // Ensures the twist is zero at the start and end
    }

    curveVertex(x + twist * swap, y + twist);
  }

  curveVertex(x2, y2); // End point
  endShape();
}

class RadioCommunication {
  constructor(x1, y1, x2, y2, maxEmit, label) {
    this.x1 = x1 // Starting point x-coordinate
    this.y1 = y1 // Starting point y-coordinate
    this.x2 = x2 // Ending point x-coordinate
    this.y2 = y2 // Ending point y-coordinate
    this.angle = atan2(y2 - y1, x2 - x1)
    this.d = dist(x1, y1, x2, y2)
    this.maxEmit = maxEmit // Number of arcs to emit

    this.speed = map(this.d, 0, dist(0, 0, width * 0.5, height * 0.5), 15, 40) // Speed of wave expansion
    this.arcAngle = TWO_PI * 0.03 // Size of the arc

    this.radii = []
    this.col = []
    this.emitting = false
    this.emitCount = 0
    this.dead = false
    this.label = label

    this.initEmit()
  }

  initEmit() {
    if (this.emitting == false) {
      this.emitting = true
    }
  }

  addWave(col) {
    this.radii.push(10)
    this.col.push(col)
    this.emitCount++
  }

  draw() {
    //strokeWeight(1)
    //stroke(1, 0, 0)
    //line(this.x1, this.y1, this.x2, this.y2)
    if (this.emitting) {
      for (var i = this.radii.length - 1; i > 0; i--) {
        stroke(this.col[i])
        strokeWeight(2)
        strokeCap(PROJECT)
        noFill()
        this.radii[i] += this.speed
        if (this.radii[i] / 2 < this.d) {
          arc(this.x1, this.y1, this.radii[i], this.radii[i], this.angle - this.arcAngle / 2, this.angle + this.arcAngle / 2)
        }
        else {
          this.radii.splice(i, 1)
          if (this.radii.length == 1) {
            this.dead = true
          }
        }
      }
      if (this.emitCount < this.maxEmit) {
        this.addWave(color(0, 0.5))
      }
    }
  }
}

function minNum(array) {
  // Filter out non-numeric values
  let numericValues = array.filter(value => typeof value === 'number' && !isNaN(value));

  // Return the minimum value, or some default (like null) if the array is empty
  return numericValues.length > 0 ? Math.min(...numericValues) : null;
}


function maxNum(array) {
  // Filter out non-numeric values
  let numericValues = array.filter(value => typeof value === 'number' && !isNaN(value));

  // Return the maximum value, or some default (like null) if the array is empty
  return numericValues.length > 0 ? Math.max(...numericValues) : null;
}

function containsNumber(arr) {
  return arr.some(function (element) {
    return typeof element === 'number';
  });
}

function findLastNumericPosition(arr) {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (typeof arr[i] === 'number') {
      return i;
    }
  }
  return -1; // Return -1 if no numeric element is found
}

function findClosest(arr, target) {
  return arr.reduce((prev, curr, index) =>
    Math.abs(curr - target) < Math.abs(arr[prev] - target) ? index : prev, 0);
}

