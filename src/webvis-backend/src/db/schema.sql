CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(32) UNIQUE NOT NULL,
  pass_hash CHAR(60) NOT NULL,
  role ENUM('admin','user') NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS sensor_readings (
  ts BIGINT PRIMARY KEY,
  temp FLOAT,
  pressure FLOAT,
  humidity FLOAT,
  light FLOAT,
  gas FLOAT
);

CREATE TABLE IF NOT EXISTS detections (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ts BIGINT NOT NULL,
  frame_id VARCHAR(64) NOT NULL,
  image_url MEDIUMTEXT NOT NULL,
  aruco_id INT,
  valve_state ENUM('open','closed'),
  conf FLOAT,
  bbox JSON,
  INDEX (ts)
);

CREATE TABLE IF NOT EXISTS poses (
  ts BIGINT PRIMARY KEY,
  x FLOAT NOT NULL,
  y FLOAT NOT NULL,
  z FLOAT NOT NULL
);

CREATE TABLE IF NOT EXISTS ops_log (
  ts BIGINT PRIMARY KEY,
  level ENUM('INFO','WARN','ERROR') NOT NULL,
  message TEXT NOT NULL
);
