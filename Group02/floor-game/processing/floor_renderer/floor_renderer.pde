import oscP5.*;
import netP5.*;
import processing.data.JSONObject;
import processing.data.JSONArray;

OscP5 oscP5;
NetAddress pythonServer;

String prompt = "Waiting for state...";
int roundNumber = 1;
int timeLeft = 30;

int housingVotes = 0, greenVotes = 0, mobilityVotes = 0;
int occHousing = 0, occGreen = 0, occMobility = 0;

// people + metrics
JSONArray peopleArr = new JSONArray();
int peopleCount = 0;
float avgSpeed = 0;
float maxSpeed = 0;
float dwellSeconds = 5.0;

// story
String storyPath = "NORMAL";
String storyTitle = "";
String storySituation = "";
String optH = "";
String optG = "";
String optM = "";
String lastResult = "";

// city HUD (0..100)
int cityHousing = 50;
int cityGreen = 50;
int cityMobility = 50;
int citySocial = 50;
int cityBudget = 50;

void setup() {
  size(1000, 650);
  textAlign(CENTER, CENTER);
  smooth();

  oscP5 = new OscP5(this, 9000);
  pythonServer = new NetAddress("127.0.0.1", 8000);
}

void draw() {
  background(20);

  fill(255);
  textSize(18);
  text("Round " + roundNumber + "  |  " + timeLeft + "s left", width/2, 26);

  textSize(14);
  text(prompt, width/2, 50);

  drawStoryPanel();

  int y0 = 170;
  int zoneH = height - 300;
  int zoneW = width / 3;

  drawZone(0 * zoneW, y0, zoneW, zoneH, "HOUSING");
  drawZone(1 * zoneW, y0, zoneW, zoneH, "GREEN");
  drawZone(2 * zoneW, y0, zoneW, zoneH, "MOBILITY");

  drawPeopleWithDwell(0, y0, width, zoneH);

  fill(255);
  textSize(16);
  text("HOUSING votes: " + housingVotes, width/6, height - 110);
  text("GREEN votes: " + greenVotes, width/2, height - 110);
  text("MOBILITY votes: " + mobilityVotes, 5*width/6, height - 110);

  textSize(12);
  text("people: " + peopleCount + " | avg speed: " + nf(avgSpeed, 1, 3) + " | max speed: " + nf(maxSpeed, 1, 3) +
       " | dwell: " + nf(dwellSeconds, 1, 1) + "s",
       width/2, height - 88);

  drawDensityBars();
  drawCityHUD();
}

void drawStoryPanel() {
  noStroke();
  fill(0, 120);
  rect(30, 65, width-60, 90);

  fill(255);
  textAlign(LEFT, TOP);
  textSize(16);
  text(storyTitle, 50, 75);

  textSize(11);
  text("PATH: " + storyPath, 50, 92);

  textSize(12);
  text(storySituation, 50, 106);

  textSize(12);
  text("HOUSING: " + optH, 50, 130);
  text("GREEN:   " + optG, 50, 147);
  text("MOBILITY: " + optM, 50, 164);

  textAlign(RIGHT, TOP);
  textSize(12);
  text(lastResult, width-50, 125);

  textAlign(CENTER, CENTER);
}

void drawCityHUD() {
  int y = height - 60;
  int x0 = 50;
  int w = width - 100;
  int h = 45;

  noStroke();
  fill(0, 120);
  rect(x0, y, w, h);

  int barW = (w - 40) / 5;
  int bx = x0 + 20;
  int by = y + 10;

  drawStatBar(bx + 0*barW, by, barW-10, 10, "Housing", cityHousing);
  drawStatBar(bx + 1*barW, by, barW-10, 10, "Green", cityGreen);
  drawStatBar(bx + 2*barW, by, barW-10, 10, "Mobility", cityMobility);
  drawStatBar(bx + 3*barW, by, barW-10, 10, "Social", citySocial);
  drawStatBar(bx + 4*barW, by, barW-10, 10, "Budget", cityBudget);
}

void drawStatBar(int x, int y, int w, int h, String label, int val) {
  stroke(255);
  noFill();
  rect(x, y, w, h);

  noStroke();
  fill(255);
  rect(x, y, (int)(w * (val/100.0)), h);

  fill(255);
  textAlign(CENTER, TOP);
  textSize(10);
  text(label + ": " + val, x + w/2, y + 14);
  textAlign(CENTER, CENTER);
}

void drawZone(int x, int y, int w, int h, String label) {
  stroke(255);
  noFill();
  rect(x, y, w, h);

  fill(255);
  textSize(22);
  text(label, x + w/2, y + h/2);
}

void drawDensityBars() {
  int barY = height - 40;
  int barH = 10;

  int maxVal = max(1, max(occHousing, max(occGreen, occMobility)));
  float a = occHousing / (float)maxVal;
  float b = occGreen / (float)maxVal;
  float c = occMobility / (float)maxVal;

  stroke(255);
  noFill();
  rect(50, barY, width-100, barH);

  int segW = (width-100)/3;
  noStroke();

  fill(255);
  rect(50 + 0*segW, barY, segW*a, barH);
  fill(200);
  rect(50 + 1*segW, barY, segW*b, barH);
  fill(150);
  rect(50 + 2*segW, barY, segW*c, barH);

  fill(255);
  textSize(12);
  text("occupancy (people in zone): H " + occHousing + " | G " + occGreen + " | M " + occMobility,
       width/2, barY - 16);
}

void drawPeopleWithDwell(int x, int y, int w, int h) {
  if (peopleArr == null) return;

  for (int i = 0; i < peopleArr.size(); i++) {
    JSONObject p = peopleArr.getJSONObject(i);
    if (p == null) continue;

    float nx = p.getFloat("x");
    float ny = p.getFloat("y");
    float sp = p.hasKey("speed") ? p.getFloat("speed") : 0;

    float prog = p.hasKey("dwell_progress") ? p.getFloat("dwell_progress") : 0;
    boolean ready = p.hasKey("ready") ? p.getBoolean("ready") : false;

    float px = x + nx*w;
    float py = y + ny*h;

    float r = 10 + sp*60;
    r = constrain(r, 10, 28);

    noStroke();
    fill(255);
    ellipse(px, py, r, r);

    float ringR = r + 12;
    stroke(255);
    noFill();
    ellipse(px, py, ringR, ringR);

    float a = prog * TWO_PI;
    strokeWeight(ready ? 4 : 2);
    arc(px, py, ringR, ringR, -HALF_PI, -HALF_PI + a);
    strokeWeight(1);
  }
}

void mousePressed() {
  String zone = zoneUnderMouse();
  if (zone != null) {
    OscMessage msg = new OscMessage("/game/zone_click");
    msg.add(zone);
    oscP5.send(msg, pythonServer);
  }
}

String zoneUnderMouse() {
  int y0 = 170;
  int h = height - 300;
  if (mouseY < y0 || mouseY > y0 + h) return null;

  int w = width / 3;
  if (mouseX < w) return "HOUSING";
  if (mouseX < 2*w) return "GREEN";
  return "MOBILITY";
}

void oscEvent(OscMessage msg) {
  if (msg.checkTypetag("s") == false) return;

  String addr = msg.addrPattern();
  String jsonStr = msg.get(0).stringValue();
  JSONObject obj = parseJSONObject(jsonStr);
  if (obj == null) return;

  if (addr.equals("/game/core")) {
    roundNumber = obj.getInt("round");
    timeLeft = obj.getInt("time_left");
    prompt = obj.getString("prompt");
    lastResult = obj.getString("last_result");
    dwellSeconds = obj.getFloat("dwell_seconds");

    JSONObject scores = obj.getJSONObject("scores");
    housingVotes = scores.getInt("HOUSING");
    greenVotes = scores.getInt("GREEN");
    mobilityVotes = scores.getInt("MOBILITY");

    JSONObject occ = obj.getJSONObject("zone_counts");
    occHousing = occ.getInt("HOUSING");
    occGreen = occ.getInt("GREEN");
    occMobility = occ.getInt("MOBILITY");
  }

  if (addr.equals("/game/story")) {
    storyPath = obj.getString("path");
    storyTitle = obj.getString("title");
    storySituation = obj.getString("situation");
    JSONObject opts = obj.getJSONObject("options");
    if (opts != null) {
      optH = opts.getString("HOUSING");
      optG = opts.getString("GREEN");
      optM = opts.getString("MOBILITY");
    }
  }

  if (addr.equals("/game/city")) {
    cityHousing = obj.getInt("housing");
    cityGreen = obj.getInt("green");
    cityMobility = obj.getInt("mobility");
    citySocial = obj.getInt("social");
    cityBudget = obj.getInt("budget");
  }

  if (addr.equals("/game/people")) {
    // people is sent as JSON array string, but wrapped here in an object? no:
    // in python we send json.dumps(list) -> parseJSONObject fails. So we must parse array.
    // We'll handle it below in a safe way:
  }

  // Special handling: /game/people is a JSON ARRAY string, not an object
  if (addr.equals("/game/people")) {
    JSONArray arr = parseJSONArray(jsonStr);
    if (arr != null) {
      peopleArr = arr;
      peopleCount = peopleArr.size();

      // compute avg/max speed locally (optional)
      float sum = 0;
      float mx = 0;
      for (int i = 0; i < peopleArr.size(); i++) {
        JSONObject p = peopleArr.getJSONObject(i);
        if (p != null && p.hasKey("speed")) {
          float sp = p.getFloat("speed");
          sum += sp;
          if (sp > mx) mx = sp;
        }
      }
      avgSpeed = (peopleCount > 0) ? (sum / peopleCount) : 0;
      maxSpeed = mx;
    }
  }
}