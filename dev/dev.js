var radioCommList = []

function setup() {
  createCanvas(800, 600)
  colorMode(RGB, 1)
}

function draw() {
  background(1)
  for (var i = radioCommList.length-1; i >= 0; i--) {
    radioCommList[i].draw()
    if (radioCommList[i].dead) {
      radioCommList.splice(i, 1)
    }
  }
}

function mousePressed() {
  radioCommList.push(new RadioCommunication(mouseX, mouseY, width * 0.5, height * 0.5, 10))
}

class RadioCommunication {
  constructor(x1, y1, x2, y2, maxEmit) {
    this.x1 = x1 // Starting point x-coordinate
    this.y1 = y1 // Starting point y-coordinate
    this.x2 = x2 // Ending point x-coordinate
    this.y2 = y2 // Ending point y-coordinate
    this.angle = atan2(y2 - y1, x2 - x1)
    this.d = dist(x1, y1, x2, y2)
    this.maxEmit = maxEmit // Number of arcs to emit

    this.speed = 40 // Speed of wave expansion
    this.arcAngle = TWO_PI * 0.1 // Size of the arc

    this.radii = []
    this.col = []
    this.emitting = false
    this.emitCount = 0
    this.dead = false

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
    strokeWeight(1)
    stroke(1, 0, 0)
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
        this.addWave(color(0, map(sin(map(this.emitCount, 0, this.maxEmit, 0, TWO_PI)), -1, 1, 0.1, 0.2)))
      }
    }
  }
}
