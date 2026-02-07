import oscP5.*;
import netP5.*;
import processing.data.JSONObject;
import processing.data.JSONArray;

OscP5 oscP5;
NetAddress pythonServer;

String prompt = "Waiting for Python state...";
int roundNumber = 1;
int timeLeft = 30;

int housingVotes = 0, greenVotes = 0, mobilityVotes = 0;
int occHousing = 0, occGreen = 0, occMobility = 0;

// heatmap data from Python
int gridW = 16;
int gridH = 9;
int[] heat = new int[16 * 9];

// people data
JSONArray peopleArr = new JSONArray();
int peopleCount = 0;
float avgSpeed = 0;
float maxSpeed = 0;

void setup() {
  size(1000, 600);
  textAlign(CENTER, CENTER);

  // Listen for OSC from Python
  oscP5 = new OscP5(this, 9000);

  // Send OSC events to Python
  pythonServer = new NetAddress("127.0.0.1", 8000);
}

void draw() {
  background(20);

  // Header
  fill(255);
  textSize(18);
  text("Round " + roundNumber + "  |  " + timeLeft + "s left", width/2, 30);

  textSize(16);
  text(prompt, width/2, 60);

  // Zones layout
  int y0 = 90;
  int zoneH = height - 220;
  int zoneW = width / 3;

  drawZone(0 * zoneW, y0, zoneW, zoneH, "HOUSING");
  drawZone(1 * zoneW, y0, zoneW, zoneH, "GREEN");
  drawZone(2 * zoneW, y0, zoneW, zoneH, "MOBILITY");

  // Heatmap overlay in the zone area
  drawHeatmap(0, y0, width, zoneH);

  // Draw people dots on top (fake YOLO / future real detections)
  drawPeople(0, y0, width, zoneH);

  // Footer: votes
  fill(255);
  textSize(16);
  text("HOUSING votes: " + housingVotes, width/6, height - 95);
  text("GREEN votes: " + greenVotes, width/2, height - 95);
  text("MOBILITY votes: " + mobilityVotes, 5 * width/6, height - 95);

  // Footer: quantitative outputs
  textSize(12);
  text("people: " + peopleCount + " | avg speed: " + nf(avgSpeed, 1, 3) + " | max speed: " + nf(maxSpeed, 1, 3),
       width/2, height - 70);

  drawDensityBars();
}

void drawZone(int x, int y, int w, int h, String label) {
  stroke(255);
  noFill();
  rect(x, y, w, h);

  fill(255);
  textSize(24);
  text(label, x + w/2, y + h/2);
}

void drawDensityBars() {
  int barY = height - 35;
  int barH = 10;

  int maxVal = max(1, max(occHousing, max(occGreen, occMobility)));

  float a = occHousing / (float)maxVal;
  float b = occGreen / (float)maxVal;
  float c = occMobility / (float)maxVal;

  stroke(255);
  noFill();
  rect(50, barY, width - 100, barH);

  int segW = (width - 100) / 3;
  noStroke();

  fill(255);
  rect(50 + 0 * segW, barY, segW * a, barH);

  fill(200);
  rect(50 + 1 * segW, barY, segW * b, barH);

  fill(150);
  rect(50 + 2 * segW, barY, segW * c, barH);

  fill(255);
  textSize(12);
  text("density samples (people in zone): H " + occHousing + " | G " + occGreen + " | M " + occMobility,
       width/2, barY - 18);
}

void drawHeatmap(int x, int y, int w, int h) {
  if (heat == null || heat.length == 0) return;

  int maxHeat = 0;
  for (int i = 0; i < heat.length; i++) {
    if (heat[i] > maxHeat) maxHeat = heat[i];
  }
  maxHeat = max(1, maxHeat);

  int cellW = max(1, w / gridW);
  int cellH = max(1, h / gridH);

  noStroke();
  for (int gy = 0; gy < gridH; gy++) {
    for (int gx = 0; gx < gridW; gx++) {
      int idx = gy * gridW + gx;
      float v = heat[idx] / (float)maxHeat; // 0..1

      // subtle overlay
      fill(255, 255 * v * 0.35);
      rect(x + gx * cellW, y + gy * cellH, cellW, cellH);
    }
  }
}

void drawPeople(int x, int y, int w, int h) {
  if (peopleArr == null) return;

  noStroke();
  fill(255);

  for (int i = 0; i < peopleArr.size(); i++) {
    JSONObject p = peopleArr.getJSONObject(i);
    if (p == null) continue;

    float nx = p.getFloat("x");
    float ny = p.getFloat("y");
    float sp = p.hasKey("speed") ? p.getFloat("speed") : 0;

    float px = x + nx * w;
    float py = y + ny * h;

    // dot size depends on speed
    float r = 10 + sp * 60;
    r = constrain(r, 10, 30);

    ellipse(px, py, r, r);
  }
}

void mousePressed() {
  // manual voting still works
  String zone = zoneUnderMouse();
  if (zone != null) {
    OscMessage msg = new OscMessage("/game/zone_click");
    msg.add(zone);
    // (optional coords, but Python accepts missing values)
    oscP5.send(msg, pythonServer);
    prompt = "Clicked: " + zone + " (sent to Python)";
  }
}

String zoneUnderMouse() {
  int y0 = 90;
  int h = height - 220;
  if (mouseY < y0 || mouseY > y0 + h) return null;

  int w = width / 3;
  if (mouseX < w) return "HOUSING";
  if (mouseX < 2 * w) return "GREEN";
  return "MOBILITY";
}

void oscEvent(OscMessage msg) {
  if (msg.checkAddrPattern("/game/state") && msg.checkTypetag("s")) {
    String jsonStr = msg.get(0).stringValue();
    JSONObject obj = parseJSONObject(jsonStr);

    if (obj != null) {
      prompt = obj.getString("prompt");
      roundNumber = obj.getInt("round");
      timeLeft = obj.getInt("time_left");

      JSONObject scores = obj.getJSONObject("scores");
      housingVotes = scores.getInt("HOUSING");
      greenVotes = scores.getInt("GREEN");
      mobilityVotes = scores.getInt("MOBILITY");

      JSONObject occ = obj.getJSONObject("zone_counts");
      occHousing = occ.getInt("HOUSING");
      occGreen = occ.getInt("GREEN");
      occMobility = occ.getInt("MOBILITY");

      gridW = obj.getInt("grid_w");
      gridH = obj.getInt("grid_h");

      JSONArray hm = obj.getJSONArray("heatmap");
      if (hm != null) {
        heat = new int[hm.size()];
        for (int i = 0; i < hm.size(); i++) {
          heat[i] = hm.getInt(i);
        }
      }

      // people + metrics
      peopleArr = obj.getJSONArray("people");
      peopleCount = obj.getInt("people_count");
      avgSpeed = obj.getFloat("avg_speed");
      maxSpeed = obj.getFloat("max_speed");
    }
  }
}