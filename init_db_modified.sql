-- ===============================================================
-- Social‑Media Analysis Schema  —  updated with repost_post_id
-- ===============================================================

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS AnalysisResult;
DROP TABLE IF EXISTS ProjectField;
DROP TABLE IF EXISTS ProjectPost;
DROP TABLE IF EXISTS Project;
DROP TABLE IF EXISTS Repost;
DROP TABLE IF EXISTS Post;
DROP TABLE IF EXISTS `User`;
DROP TABLE IF EXISTS SocialMedia;
DROP TABLE IF EXISTS Institute;
SET FOREIGN_KEY_CHECKS = 1;

CREATE DATABASE IF NOT EXISTS SocialMediaAnalysis;
USE SocialMediaAnalysis;

-- 1. Institutes
CREATE TABLE Institute (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
);

-- 2. Social media platforms
CREATE TABLE SocialMedia (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50)  NOT NULL UNIQUE
);

-- 3. Users
CREATE TABLE `User` (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  username             VARCHAR(40) NOT NULL,
  social_media_id      INT         NOT NULL,
  first_name           VARCHAR(50),
  last_name            VARCHAR(50),
  country_of_birth     VARCHAR(50),
  country_of_residence VARCHAR(50),
  age                  INT,
  gender               ENUM('male','female','non_binary','other') DEFAULT NULL,
  verified             BOOLEAN     DEFAULT FALSE,
  UNIQUE (username, social_media_id),
  FOREIGN KEY (social_media_id) REFERENCES SocialMedia(id)
);

-- 4. Posts
CREATE TABLE Post (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  user_id          INT              NOT NULL,
  social_media_id  INT              NOT NULL,
  post_time        DATETIME         NOT NULL,
  content          TEXT,
  city             VARCHAR(100),
  state            VARCHAR(100),
  country          VARCHAR(100),
  likes            INT  DEFAULT 0   CHECK (likes >= 0),
  dislikes         INT  DEFAULT 0   CHECK (dislikes >= 0),
  multimedia       BOOLEAN DEFAULT FALSE,
  media_url        TEXT,
  UNIQUE(user_id, social_media_id, post_time),
  FOREIGN KEY (user_id)         REFERENCES `User`(id),
  FOREIGN KEY (social_media_id) REFERENCES SocialMedia(id)
);
CREATE INDEX idx_social_time ON Post(social_media_id, post_time);

-- 5. Reposts (now links both original and the new repost‐Post row)
CREATE TABLE Repost (
  id                 INT AUTO_INCREMENT PRIMARY KEY,
  original_post_id   INT              NOT NULL,
  repost_post_id     INT              NOT NULL,
  reposter_id        INT              NOT NULL,
  repost_time        DATETIME         NOT NULL,
  UNIQUE(original_post_id, repost_post_id),
  FOREIGN KEY (original_post_id) REFERENCES Post(id),
  FOREIGN KEY (repost_post_id)   REFERENCES Post(id),
  FOREIGN KEY (reposter_id)      REFERENCES `User`(id)
);

-- 6. Projects
CREATE TABLE Project (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  name                 VARCHAR(100) NOT NULL UNIQUE,
  manager_first_name   VARCHAR(50),
  manager_last_name    VARCHAR(50),
  institute_id         INT,
  start_date           DATE   NOT NULL,
  end_date             DATE   NOT NULL,
  CHECK (end_date >= start_date),
  FOREIGN KEY (institute_id) REFERENCES Institute(id)
);

-- 7. Link posts ↔ projects
CREATE TABLE ProjectPost (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  project_id  INT NOT NULL,
  post_id     INT NOT NULL,
  UNIQUE(project_id, post_id),
  FOREIGN KEY (project_id) REFERENCES Project(id),
  FOREIGN KEY (post_id)    REFERENCES Post(id)
);

-- 8. Per‑project dynamic fields
CREATE TABLE ProjectField (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  project_id INT              NOT NULL,
  name       VARCHAR(100)     NOT NULL,
  UNIQUE (project_id, name),
  FOREIGN KEY (project_id) REFERENCES Project(id)
);

-- 9. Analysis results
CREATE TABLE AnalysisResult (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  project_post_id  INT              NOT NULL,
  field_id         INT              NOT NULL,
  value            TEXT,
  UNIQUE(project_post_id, field_id),
  FOREIGN KEY (project_post_id) REFERENCES ProjectPost(id),
  FOREIGN KEY (field_id)          REFERENCES ProjectField(id)
);

-- 10. Helpful indexes
CREATE INDEX idx_user_social ON `User`(username, social_media_id);
CREATE INDEX idx_pp_project  ON ProjectPost(project_id);
CREATE INDEX idx_pp_post     ON ProjectPost(post_id);
