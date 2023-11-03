// p5.js sketch
function setup() {
    createCanvas(windowWidth, windowHeight);
    background(100); // A gray background: you can change it
}

function draw() {
    // Your drawing code goes here
    fill(255, 125, 0); // Fill with red color
    noStroke();
    ellipse(mouseX, mouseY, 50, 50); // Draw an ellipse at the position of the mouse
}

// This function automatically resizes the canvas when the window is resized
function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}