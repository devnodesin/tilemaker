let scene, camera, renderer, roomMesh;
let selectedFloorFile = null;
let wallTileData = []; // { id: string, file: File | null, rows: number, previewUrl: string | null }
const WALL_TILE_FIXED_LENGTH = 1.5; // ft
const WALL_TILE_FIXED_HEIGHT = 1.0; // ft
let ambientLight, pointLight;
let currentGroutGap = 1; // Default grout gap in pixels

// DOM Elements
const outputContainer = document.getElementById("output-container");
const navbar = document.querySelector(".navbar");
const ceilingColorInput = document.getElementById("ceiling-color");
const brightnessSlider = document.getElementById("brightness-slider");
const brightnessValueSpan = document.getElementById("brightness-value");
const cameraAngleSlider = document.getElementById("camera-angle-slider");
const cameraAngleValueSpan = document.getElementById("camera-angle-value");
const cameraDepthSlider = document.getElementById("camera-depth-slider");
const cameraDepthValueSpan = document.getElementById("camera-depth-value");
const cameraPanSlider = document.getElementById("camera-pan-slider");
const cameraPanValueSpan = document.getElementById("camera-pan-value");
const groutGapSlider = document.getElementById("grout-gap-slider");
const groutGapValueSpan = document.getElementById("grout-gap-value");
const floorDropZone = document.getElementById("floor-drop-zone");
const floorTextureInput = document.getElementById("floor-texture-file");
const floorPreview = document.getElementById("floor-preview");
const tileSizeInput = document.getElementById("tile-size");
const wallTilesContainer = document.getElementById("wall-tiles-container");
const addWallRowBtn = document.getElementById("add-wall-row-btn");

// Three.js Setup
const textureLoader = new THREE.TextureLoader();

function initThree() {
  scene = new THREE.Scene();
  // Set dark background directly
  scene.background = new THREE.Color(0x404040);

  const aspect = 1; // Fixed aspect ratio for the square container
  camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 1000);
  const initialLength = 8; // Fixed initial length
  // Store initial camera state details for slider calculations
  camera.userData.initialLookAt = new THREE.Vector3(0, 0, -initialLength / 2);
  camera.userData.initialY = 0;
  camera.userData.initialX = 0;
  camera.userData.initialZOffset = 1.0; // Base offset factor for zoom

  renderer = new THREE.WebGLRenderer({
    antialias: true,
    preserveDrawingBuffer: true,
  }); // preserveDrawingBuffer for download
  renderer.setSize(outputContainer.clientWidth, outputContainer.clientWidth);
  outputContainer.appendChild(renderer.domElement);

  ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);
  pointLight = new THREE.PointLight(0xffffff, 0.8);
  pointLight.position.set(0, 2, 2); // Adjust as needed
  scene.add(pointLight);

  window.addEventListener("resize", onWindowResize, false);
}

function updateLightIntensity() {
  if (!ambientLight || !pointLight || !brightnessSlider) return;
  const brightness = parseFloat(brightnessSlider.value);
  ambientLight.intensity = 0.6 * brightness;
  pointLight.intensity = 0.8 * brightness;
  if (brightnessValueSpan)
    brightnessValueSpan.textContent = brightness.toFixed(1);
  requestRender();
}

// Renamed from updateCameraAngle
function updateCameraTilt() {
  if (!camera || !cameraAngleSlider || !cameraAngleValueSpan) return;
  const angleDegrees = parseFloat(cameraAngleSlider.value);
  const angleRadians = THREE.MathUtils.degToRad(angleDegrees);
  const lookAtPoint = camera.userData.initialLookAt; // Base lookAt point
  const initialLookAtY = lookAtPoint ? lookAtPoint.y : 0;
  const initialY = camera.userData.initialY || 0;
  const baseZOffset = camera.userData.initialZOffset || 1.0; // Use the base offset for consistent tilt sensitivity

  // Simplified tilt: Adjust Y position and lookAt target Y slightly
  const yOffset = Math.tan(angleRadians) * baseZOffset * 5; // Sensitivity factor
  const roomLength = 8; // Fixed room length
  const lookAtYOffset = Math.tan(angleRadians) * (roomLength / 2) * 0.5; // Adjust target slightly

  camera.position.y = initialY + yOffset;
  // Adjust lookAt target based on current pan
  const currentLookAtX =
    camera.userData.currentLookAtX || (lookAtPoint ? lookAtPoint.x : 0);
  camera.lookAt(
    currentLookAtX,
    initialLookAtY + lookAtYOffset,
    lookAtPoint ? lookAtPoint.z : -10
  );

  camera.updateProjectionMatrix();
  cameraAngleValueSpan.textContent = angleDegrees.toFixed(0);
  requestRender();
}

// Renamed from updateCameraDepth
function updateCameraZoom() {
  if (!camera || !cameraDepthSlider || !cameraDepthValueSpan) return;
  const zoomFactor = parseFloat(cameraDepthSlider.value);
  const roomLength = 8; // Fixed room length
  const baseZOffset = camera.userData.initialZOffset || 1.0;
  const newZOffset = baseZOffset * zoomFactor;

  camera.position.z = roomLength / 2 - newZOffset;
  cameraDepthValueSpan.textContent = zoomFactor.toFixed(1);
  requestRender();
}

function updateCameraPan() {
  if (!camera || !cameraPanSlider || !cameraPanValueSpan) return;
  const panValue = parseFloat(cameraPanSlider.value);
  const initialLookAt = camera.userData.initialLookAt;
  const initialX = camera.userData.initialX || 0;

  camera.position.x = initialX + panValue;

  // Adjust lookAt X to keep view parallel
  const newLookAt = initialLookAt.clone();
  newLookAt.x = initialX + panValue;
  camera.userData.currentLookAtX = newLookAt.x; // Store current lookAt X for tilt function
  camera.lookAt(newLookAt);

  camera.updateProjectionMatrix();
  cameraPanValueSpan.textContent = panValue.toFixed(1);
  requestRender(); // Pan also affects tilt's lookAt, so call it
  updateCameraTilt(); // Re-apply tilt based on new pan/lookAt
}

function updateGroutGap() {
  if (!groutGapSlider || !groutGapValueSpan) return;
  currentGroutGap = parseInt(groutGapSlider.value, 10);
  groutGapValueSpan.textContent = currentGroutGap;
  // Regenerate room because wall textures depend on this
  generateRoom();
}

function updateFloorPreview(file) {
  if (file && file.type.startsWith("image/")) {
    const reader = new FileReader();
    reader.onload = (e) => {
      floorPreview.src = e.target.result;
      floorPreview.style.display = "block";
    };
    reader.readAsDataURL(file);
  } else {
    floorPreview.src = "";
    floorPreview.style.display = "none";
    selectedFloorFile = null;
    // floorTextureInput.value = ''; // Optional reset
  }
}

function addWallTileRow(initialData = null) {
  const rowId = `wall-row-${Date.now()}-${Math.random()
    .toString(36)
    .substring(2, 7)}`;
  const rowDiv = document.createElement("div");
  rowDiv.className = "wall-tile-row row"; // Add 'row' for BS grid
  rowDiv.id = rowId;
  rowDiv.innerHTML = `
                <div class="col-xs-4"> <!-- Input field and delete button in one row -->
                    <div class="form-group flex flex-column">
                        <input type="number" class="form-control input-sm" id="wall-rows-${rowId}" value="${
    initialData?.rows || 1
  }" min="1" placeholder="Tile Rows" style="margin-right: 5px;">

                        <div class="input-group margin-top-10">
                            <button type="button" class="btn btn-danger btn-xs" aria-label="Delete row">
                                <span class="glyphicon glyphicon-trash"></span>
                            </button>
                            <span class="input-group-addon" style="padding:0 8px;">
                                <div class="form-check form-switch" style="margin-bottom:0;">
                                    <input class="form-check-input flip-image-switch" type="checkbox" id="flip-switch-${rowId}">
                                    <label class="form-check-label" for="flip-switch-${rowId}" style="margin:0; cursor:pointer;">Flip</label>
                                </div>
                            </span>
                        </div>

                        
                    </div>
                </div>
                <div class="col-xs-8"> <!-- Drop zone -->
                    <div class="image-drop-zone wall-drop-zone" aria-label="Drop or click wall tile image">
                        <i class="bi bi-image" style="display: block;"></i>
                        <span style="display: block;">Drop/Click</span>
                        <img class="preview wall-preview" alt="Wall tile preview" style="display: none;">
                        <input type="file" class="wall-texture-file" accept="image/*" aria-label="Wall tile file input">
                    </div>
                </div>
            `;
  wallTilesContainer.appendChild(rowDiv);

  const newRowData = {
    id: rowId,
    file: initialData?.file || null,
    rows: initialData?.rows || 1,
    previewUrl: initialData?.previewUrl || null,
    flipped: false, // Initialize flipped state
  };
  wallTileData.push(newRowData);

  // Get elements and add listeners
  const dropZone = rowDiv.querySelector(".wall-drop-zone");
  const fileInput = rowDiv.querySelector(".wall-texture-file");
  const preview = rowDiv.querySelector(".wall-preview");
  // Select input by ID
  const rowsInput = document.getElementById(`wall-rows-${rowId}`);
  // Select delete button more specifically within the rowDiv
  const deleteBtn = rowDiv.querySelector("button.btn-danger");
  // Select flip switch by ID
  const flipSwitch = document.getElementById(`flip-switch-${rowId}`);

  if (newRowData.previewUrl) {
    preview.src = newRowData.previewUrl;
    preview.style.display = "block";
  }

  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (event) =>
    handleWallFileChange(event, newRowData, preview)
  );
  // Ensure rowsInput exists before adding listener
  if (rowsInput) {
    rowsInput.addEventListener("input", (event) => {
      newRowData.rows = parseInt(event.target.value, 10) || 1;
    });
  }
  // Ensure deleteBtn exists before adding listener
  if (deleteBtn) {
    deleteBtn.addEventListener("click", () => deleteWallTileRow(rowId));
  }
  // Ensure flipSwitch exists before adding listener
  if (flipSwitch) {
    flipSwitch.addEventListener("change", (event) => {
      newRowData.flipped = event.target.checked;
    });
  }

  // Drag and Drop listeners for wall tiles
  setupDropZone(dropZone, fileInput, (file) =>
    handleWallFileChange({ target: { files: [file] } }, newRowData, preview)
  );
}

function handleWallFileChange(event, rowData, previewElement) {
  const file = event.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      previewElement.src = e.target.result;
      previewElement.style.display = "block";
      rowData.file = file;
      rowData.previewUrl = e.target.result;
    };
    reader.readAsDataURL(file);
  } else {
    previewElement.src = "";
    previewElement.style.display = "none";
    rowData.file = null;
    rowData.previewUrl = null;
  }
}

function deleteWallTileRow(rowId) {
  const rowElement = document.getElementById(rowId);
  if (rowElement) rowElement.remove();
  wallTileData = wallTileData.filter((item) => item.id !== rowId);
}

async function generateWallTexture(
  wallWidth,
  wallHeight,
  tileConfig,
  defaultColorHex,
  groutGap
) {
  const TILE_W = WALL_TILE_FIXED_LENGTH;
  const TILE_H = WALL_TILE_FIXED_HEIGHT;
  const tilesPerRow = Math.ceil(wallWidth / TILE_W);
  const totalTileRows = Math.ceil(wallHeight / TILE_H);

  // Texture size (e.g., 128px per tile dimension) - Keep this consistent
  const baseTilePixelSize = 128;
  const textureWidth = tilesPerRow * baseTilePixelSize;
  const textureHeight = totalTileRows * baseTilePixelSize;

  // Calculate actual tile size in pixels, considering the grout gap
  const tilePixelW = baseTilePixelSize - groutGap;
  const tilePixelH = baseTilePixelSize - groutGap;

  // Ensure tile dimensions are not negative
  const finalTilePixelW = Math.max(1, tilePixelW);
  const finalTilePixelH = Math.max(1, tilePixelH);

  const canvas = document.createElement("canvas");
  canvas.width = textureWidth;
  canvas.height = textureHeight;
  const ctx = canvas.getContext("2d");

  // Fill background (this will be the grout color)
  ctx.fillStyle = defaultColorHex;
  ctx.fillRect(0, 0, textureWidth, textureHeight);

  // Load unique images efficiently
  const imagePromises = [];
  const uniqueImages = {};
  tileConfig.forEach((item) => {
    if (item.file && item.previewUrl && !uniqueImages[item.previewUrl]) {
      const promise = new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
          uniqueImages[item.previewUrl] = img;
          resolve(img);
        };
        img.onerror = reject;
        img.src = item.previewUrl;
      });
      imagePromises.push(promise);
    }
  });

  try {
    await Promise.all(imagePromises);
  } catch (error) {
    console.error("Error loading wall tile images:", error);
  }

  // Draw tiles bottom-up
  const reversedTileConfig = [...tileConfig].reverse();
  let currentTileRow = 0; // Tracks the logical tile row index (0-based from bottom)

  for (const item of reversedTileConfig) {
    if (!item.file || !item.previewUrl || !uniqueImages[item.previewUrl])
      continue;

    const img = uniqueImages[item.previewUrl];
    const numRowsForItem = item.rows;

    for (let r = 0; r < numRowsForItem && currentTileRow < totalTileRows; r++) {
      // Calculate the Y position for the top-left corner of the tile in this row
      // Start from the bottom (textureHeight), move up by tile rows and grout gaps
      const rowY =
        textureHeight - (currentTileRow + 1) * baseTilePixelSize + groutGap / 2; // Center vertically within the slot

      for (let c = 0; c < tilesPerRow; c++) {
        // Calculate the X position for the top-left corner of the tile in this column
        const colX = c * baseTilePixelSize + groutGap / 2; // Center horizontally within the slot

        if (item.flipped) {
          ctx.save();
          // Translate to the center of the tile drawing area, scale, then draw centered
          ctx.translate(colX + finalTilePixelW / 2, rowY + finalTilePixelH / 2);
          ctx.scale(1, -1); // Flip vertically
          // Draw image centered at the new origin (0,0) after translation/scaling
          ctx.drawImage(
            img,
            -finalTilePixelW / 2,
            -finalTilePixelH / 2,
            finalTilePixelW,
            finalTilePixelH
          );
          ctx.restore();
        } else {
          ctx.drawImage(img, colX, rowY, finalTilePixelW, finalTilePixelH);
        }
      }
      currentTileRow++; // Move to the next logical tile row up
    }
    if (currentTileRow >= totalTileRows) break;
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

async function generateRoom() {
  const ROOM_WIDTH = 6; // Fixed width
  const ROOM_HEIGHT = 7; // Fixed height
  const ROOM_LENGTH = 8; // Fixed length
  const ceilingColor = ceilingColorInput.value || "#ffffff";
  const wallColorHex = "#cccccc"; // This will be the grout color now
  const wallColor = new THREE.Color(wallColorHex).getHex();
  const floorColor = 0x636e72;
  const tileSize = parseFloat(tileSizeInput.value) || 1;
  const floorTextureFile = selectedFloorFile;
  const groutGap = currentGroutGap; // Use the current grout gap value
  const texturePromises = [];

  // Dispose previous resources
  if (roomMesh) {
    scene.remove(roomMesh);
    if (roomMesh.geometry) roomMesh.geometry.dispose();
    if (Array.isArray(roomMesh.material)) {
      roomMesh.material.forEach((mat) => {
        if (mat) {
          if (mat.map) mat.map.dispose();
          mat.dispose();
        }
      });
    } else if (roomMesh.material) {
      if (roomMesh.material.map) roomMesh.material.map.dispose();
      roomMesh.material.dispose();
    }
    roomMesh = null; // Clear reference
  }

  const geometry = new THREE.BoxGeometry(ROOM_WIDTH, ROOM_HEIGHT, ROOM_LENGTH);

  // Materials
  const defaultWallMaterial = new THREE.MeshStandardMaterial({
    color: wallColor,
    side: THREE.BackSide,
  });
  const ceilingMaterial = new THREE.MeshStandardMaterial({
    color: ceilingColor,
    side: THREE.BackSide,
  });
  const floorMaterial = new THREE.MeshStandardMaterial({
    color: floorColor,
    side: THREE.BackSide,
  });

  // --- Texture Loading Promises ---

  // Floor Texture
  if (floorTextureFile) {
    texturePromises.push(
      new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (event) => {
          textureLoader.load(
            event.target.result,
            (texture) => {
              texture.wrapS = THREE.RepeatWrapping;
              texture.wrapT = THREE.RepeatWrapping;
              texture.repeat.set(ROOM_WIDTH / tileSize, ROOM_LENGTH / tileSize);
              floorMaterial.map = texture;
              floorMaterial.color.set(0xffffff); // Show texture color
              floorMaterial.needsUpdate = true;
              resolve();
            },
            undefined,
            (err) => {
              console.error("Floor texture load error:", err);
              reject(err);
            }
          );
        };
        reader.onerror = (event) => {
          console.error("Floor file read error:", event.target.error);
          reject(event.target.error);
        };
        reader.readAsDataURL(floorTextureFile);
      })
    );
  }

  // Wall Textures
  let backWallMaterial = defaultWallMaterial.clone();
  let leftWallMaterial = defaultWallMaterial.clone();
  let rightWallMaterial = defaultWallMaterial.clone();
  const validWallTiles = wallTileData.filter(
    (item) => item.file && item.rows > 0
  );

  if (validWallTiles.length > 0) {
    // Pass groutGap to generateWallTexture
    texturePromises.push(
      generateWallTexture(
        ROOM_WIDTH,
        ROOM_HEIGHT,
        validWallTiles,
        wallColorHex,
        groutGap
      )
        .then((tex) => {
          if (tex)
            backWallMaterial = new THREE.MeshStandardMaterial({
              map: tex,
              side: THREE.BackSide,
              color: 0xffffff,
            });
        })
        .catch((err) => console.error("Back wall texture gen error:", err))
    );

    texturePromises.push(
      generateWallTexture(
        ROOM_LENGTH,
        ROOM_HEIGHT,
        validWallTiles,
        wallColorHex,
        groutGap
      )
        .then((tex) => {
          if (tex)
            leftWallMaterial = new THREE.MeshStandardMaterial({
              map: tex,
              side: THREE.BackSide,
              color: 0xffffff,
            });
        })
        .catch((err) => console.error("Left wall texture gen error:", err))
    );

    texturePromises.push(
      generateWallTexture(
        ROOM_LENGTH,
        ROOM_HEIGHT,
        validWallTiles,
        wallColorHex,
        groutGap
      )
        .then((tex) => {
          if (tex)
            rightWallMaterial = new THREE.MeshStandardMaterial({
              map: tex,
              side: THREE.BackSide,
              color: 0xffffff,
            });
        })
        .catch((err) => console.error("Right wall texture gen error:", err))
    );
  }

  // Wait for all textures
  try {
    await Promise.all(texturePromises);
  } catch (error) {
    console.error("Error loading/generating textures:", error);
    // Reset materials to default if promises failed? (Current catch handles individual failures)
  }

  // Update camera initial state based on new room dimensions
  camera.userData.initialLookAt = new THREE.Vector3(0, 0, -ROOM_LENGTH / 2);
  // Apply slider values to camera
  updateCameraZoom();
  updateCameraPan(); // Pan needs to be updated before tilt if it affects lookAt
  updateCameraTilt();
  updateLightIntensity();

  // Assign materials (Right, Left, Top, Bottom, Front, Back)
  const materials = [
    rightWallMaterial,
    leftWallMaterial,
    ceilingMaterial,
    floorMaterial,
    defaultWallMaterial.clone(), // Front face (viewer side) - keep default
    backWallMaterial,
  ];

  roomMesh = new THREE.Mesh(geometry, materials);
  scene.add(roomMesh);

  requestRender(); // Initial render
}

let renderRequested = false;
function requestRender() {
  if (!renderRequested && renderer && scene && camera) {
    renderRequested = true;
    requestAnimationFrame(() => {
      renderer.render(scene, camera);
      renderRequested = false;
    });
  }
}

// No separate animate loop needed if renders are only triggered by interactions
// function animate() { ... } // Removed

function onWindowResize() {
  if (camera && renderer && outputContainer) {
    const width = outputContainer.clientWidth;
    // camera.aspect stays 1
    camera.updateProjectionMatrix();
    renderer.setSize(width, width);
    requestRender(); // Re-render on resize
  }
}

function downloadJPEG() {
  if (!outputContainer || !renderer) return;
  // Ensure scene is rendered before capturing
  renderer.render(scene, camera);

  html2canvas(outputContainer, { useCORS: true, logging: false })
    .then((canvas) => {
      const link = document.createElement("a");
      link.download = "room_visualization.jpg";
      link.href = canvas.toDataURL("image/jpeg", 0.9);
      link.click();
    })
    .catch((err) => {
      console.error("Error generating JPEG:", err);
      alert("Could not generate JPEG image.");
    });
}

// --- Animation Logic ---
let animationActive = false;
let animationRequestId = null;
let animationStepIndex = 0;
let animationSteps = [];
let animationOnFinish = null;
let animationStartTime = null;
let animationCurrentStep = null;

function setupAnimationSteps() {
  // Each step: { type, from, to, duration (ms) }
  animationSteps = [
    { type: "pan", from: 0, to: -2.0, duration: 1500 },
    { type: "zoom", from: 1.0, to: 4.5, duration: 1500 },
    { type: "pan", from: -2.0, to: 0.5, duration: 1500 },
    { type: "zoom", from: 4.5, to: 2.0, duration: 1500 },
  ];
}

function resetAnimationSliders() {
  cameraPanSlider.value = 0;
  cameraDepthSlider.value = 1.0;
  updateCameraPan();
  updateCameraZoom();
}

function animatePreviewStepSmooth(timestamp) {
  if (!animationActive) {
    animationStartTime = null;
    animationCurrentStep = null;
    return;
  }
  if (animationStepIndex >= animationSteps.length) {
    animationActive = false;
    animationStepIndex = 0;
    animationStartTime = null;
    animationCurrentStep = null;
    if (typeof animationOnFinish === "function") animationOnFinish();
    return;
  }
  if (!animationStartTime) {
    animationStartTime = timestamp;
    animationCurrentStep = animationSteps[animationStepIndex];
  }
  const step = animationCurrentStep;
  const elapsed = timestamp - animationStartTime;
  const t = Math.min(1, elapsed / step.duration);
  // Ease in-out cubic
  const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const value = step.from + (step.to - step.from) * ease;

  if (step.type === "pan") {
    cameraPanSlider.value = value.toFixed(3);
    updateCameraPan();
    //console.debug(`Smooth pan: ${value}`);
  } else if (step.type === "zoom") {
    cameraDepthSlider.value = value.toFixed(3);
    updateCameraZoom();
    //console.debug(`Smooth zoom: ${value}`);
  }
  renderer.render(scene, camera);

  if (t < 1) {
    animationRequestId = requestAnimationFrame(animatePreviewStepSmooth);
  } else {
    animationStepIndex++;
    animationStartTime = null;
    animationCurrentStep = null;
    animationRequestId = requestAnimationFrame(animatePreviewStepSmooth);
  }
}

function startAnimationPreview(onFinish) {
  if (animationActive) {
    console.debug("Animation already active.");
    return;
  }
  console.debug("Starting animation preview.");
  setupAnimationSteps();
  animationStepIndex = 0;
  animationActive = true;
  animationOnFinish = onFinish || null;
  animationStartTime = null;
  animationCurrentStep = null;
  resetAnimationSliders();
  animationRequestId = requestAnimationFrame(animatePreviewStepSmooth);
}

function stopAnimationPreview() {
  animationActive = false;
  if (animationRequestId) cancelAnimationFrame(animationRequestId);
  animationRequestId = null;
  animationStepIndex = 0;
  animationOnFinish = null;
  animationStartTime = null;
  animationCurrentStep = null;
  console.debug("Animation preview stopped.");
}

// --- GIF Export ---
function downloadAnimationGIF() {
  console.debug("Starting GIF animation export.");
  setupAnimationSteps();

  let workerScriptUrl = "gif.worker.js";
  let gif = new GIF({
    workers: 2,
    quality: 10,
    width: renderer.domElement.width,
    height: renderer.domElement.height,
    workerScript: workerScriptUrl,
  });
  let stepIndex = 0;
  let steps = animationSteps.map((s) => Object.assign({}, s));
  let frameCount = 0;

  // Progress spinner setup
  const downloadBtn = document.getElementById("download-animation-btn");
  if (downloadBtn) {
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = `<span class="glyphicon glyphicon-refresh spinning"></span> Rendering...`;
  }

  // Add spinner CSS if not present
  if (!document.getElementById("gif-spinner-style")) {
    const style = document.createElement("style");
    style.id = "gif-spinner-style";
    style.innerHTML = `.spinning { animation: spin 1s linear infinite; }
                @keyframes spin { 100% { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
  }

  steps.forEach((step) => {
    if (typeof step.from === "number") {
      step.value = step.from;
      let totalFrames = 60;
      step.step = (step.to - step.from) / totalFrames;
    }
  });

  function renderAndAddFrame(cb) {
    renderer.render(scene, camera);
    gif.addFrame(renderer.domElement, { copy: true, delay: 16 });
    cb();
  }

  function nextFrame() {
    if (stepIndex >= steps.length) {
      console.debug("GIF animation steps finished, rendering GIF...");
      gif.on("progress", function (p) {
        if (downloadBtn) {
          let percent = Math.round(p * 100);
          downloadBtn.innerHTML = `<span class="glyphicon glyphicon-refresh spinning"></span> Saving... ${percent}%`;
        }
      });
      gif.on("finished", function (blob) {
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "room_animation.gif";
        a.click();
        console.debug("GIF download triggered.");
        if (downloadBtn) {
          downloadBtn.disabled = false;
          downloadBtn.innerHTML = "Download GIF";
        }
      });
      gif.render();
      return;
    }
    let step = steps[stepIndex];
    let done = false;
    if (
      typeof step.value !== "number" ||
      typeof step.step !== "number" ||
      isNaN(step.value) ||
      isNaN(step.step)
    ) {
      console.error(
        `[GIF] Invalid step value or step size at index ${stepIndex}. Skipping step.`
      );
      stepIndex++;
      setTimeout(nextFrame, 0);
      return;
    }
    if (step.type === "pan") {
      step.value += step.step;
      if (
        (step.step < 0 && step.value <= step.to) ||
        (step.step > 0 && step.value >= step.to)
      ) {
        step.value = step.to;
        done = true;
      }
      cameraPanSlider.value = step.value.toFixed(2);
      updateCameraPan();
      console.debug(`[GIF] Animating pan: ${step.value}`);
    } else if (step.type === "zoom") {
      step.value += step.step;
      if (
        (step.step < 0 && step.value <= step.to) ||
        (step.step > 0 && step.value >= step.to)
      ) {
        step.value = step.to;
        done = true;
      }
      cameraDepthSlider.value = step.value.toFixed(2);
      updateCameraZoom();
      console.debug(`[GIF] Animating zoom: ${step.value}`);
    }
    renderAndAddFrame(() => {
      frameCount++;
      if (done) stepIndex++;
      setTimeout(nextFrame, 0);
    });
  }
  resetAnimationSliders();
  nextFrame();
}

// --- Event Listeners for Animation ---
document.addEventListener("DOMContentLoaded", () => {
  // Theme Initialization Removed
  /*
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            let initialThemeIsDark = savedTheme ? (savedTheme === 'dark') : true; // Default dark
            if (!initialThemeIsDark) toggleTheme(); // Apply light theme if needed
            */

  // Ensure body has dark-mode class (it's set in HTML/CSS by default now but good practice)
  document.body.classList.add("dark-mode");
  document.body.classList.remove("light-mode"); // Ensure light-mode is removed if somehow present
  // Ensure navbar has correct class (set in HTML but good practice)
  navbar.classList.add("navbar-inverse");
  navbar.classList.remove("navbar-default");

  initThree();
  addWallTileRow(); // Add initial wall row

  // Setup Floor Drop Zone
  setupDropZone(floorDropZone, floorTextureInput, (file) => {
    selectedFloorFile = file;
    updateFloorPreview(file);
  });
  // Handle direct file input change for floor
  floorTextureInput.addEventListener("change", (event) => {
    const file = event.target.files[0];
    selectedFloorFile = file; // Update selected file
    updateFloorPreview(file); // Update preview
  });

  // Control Listeners
  document
    .getElementById("generate-room-btn")
    .addEventListener("click", generateRoom);
  document
    .getElementById("download-jpeg-btn")
    .addEventListener("click", downloadJPEG);
  addWallRowBtn.addEventListener("click", () => addWallTileRow());

  // Slider Listeners
  brightnessSlider.addEventListener("input", updateLightIntensity);
  cameraAngleSlider.addEventListener("input", updateCameraTilt);
  cameraDepthSlider.addEventListener("input", updateCameraZoom);
  cameraPanSlider.addEventListener("input", updateCameraPan);
  groutGapSlider.addEventListener("input", updateGroutGap); // Add listener for grout gap

  // Initial Setup Calls
  updateGroutGap(); // Set initial grout gap value display and variable
  generateRoom(); // Initial Render (will use initial grout gap)

  // Ensure buttons are connected after DOM is loaded
  const animatePreviewBtn = document.getElementById("animate-preview-btn");
  const downloadAnimationBtn = document.getElementById(
    "download-animation-btn"
  );

  if (animatePreviewBtn) {
    animatePreviewBtn.addEventListener("click", function () {
      console.debug("Animate Preview button clicked.");
      if (animationActive) {
        stopAnimationPreview();
        this.textContent = "Animate Preview";
      } else {
        this.textContent = "Stop Animation";
        startAnimationPreview(() => {
          animationActive = false;
          this.textContent = "Animate Preview";
          console.debug("Animation preview completed.");
        });
      }
    });
  }

  if (downloadAnimationBtn) {
    downloadAnimationBtn.addEventListener("click", function () {
      console.debug("Download Animation button clicked.");
      if (animationActive) stopAnimationPreview();
      this.disabled = true;
      this.innerHTML = `<span class="glyphicon glyphicon-refresh spinning"></span> Rendering...`;
      downloadAnimationGIF();
    });
  }
});

// --- Drag and Drop Setup ---
function setupDropZone(zone, inputElement, fileHandler) {
  zone.addEventListener("click", () => inputElement.click());
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("drag-over");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("drag-over");
    const file = event.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      // Update the input's files list to be consistent
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      inputElement.files = dataTransfer.files;
      // Call the specific handler
      fileHandler(file);
    } else if (file) {
      alert("Please drop an image file.");
    }
  });
}
