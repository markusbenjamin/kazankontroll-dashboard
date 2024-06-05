function setup() {
  let canvas = createCanvas(windowWidth, windowHeight)
  sketchAspectRatio = 1.9
  enforceAspectRatio(sketchAspectRatio)
  colorMode(RGB, 1)
  textAlign(CENTER, CENTER)
  textFont('Consolas')
  textSize(30)
}

function draw(){
  background(229 / 255, 222 / 255, 202 / 255)
  text("A fűtésszezon véget ért.",width*0.5,height*0.5)
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