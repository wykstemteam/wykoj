-- upgrade --
CREATE TABLE IF NOT EXISTS `contest` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(120) NOT NULL,
    `is_public` BOOL NOT NULL,
    `start_time` DATETIME(6) NOT NULL,
    `duration` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sidebar` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `content` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `task` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `task_id` VARCHAR(10) NOT NULL UNIQUE,
    `title` VARCHAR(120) NOT NULL,
    `is_public` BOOL NOT NULL,
    `content` LONGTEXT NOT NULL,
    `time_limit` DECIMAL(5,3) NOT NULL,
    `memory_limit` INT NOT NULL,
    `solves` INT NOT NULL  DEFAULT 0
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `user` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(30) NOT NULL UNIQUE,
    `password` VARCHAR(200) NOT NULL,
    `name` VARCHAR(30) NOT NULL,
    `english_name` VARCHAR(120) NOT NULL,
    `chesscom_username` VARCHAR(30),
    `lichess_username` VARCHAR(30),
    `language` VARCHAR(30) NOT NULL  DEFAULT 'C++',
    `img_40` VARCHAR(40) NOT NULL  DEFAULT 'default_40.png',
    `img_160` VARCHAR(40) NOT NULL  DEFAULT 'default_160.png',
    `can_edit_profile` BOOL NOT NULL  DEFAULT 1,
    `is_student` BOOL NOT NULL,
    `is_admin` BOOL NOT NULL,
    `solves` INT NOT NULL  DEFAULT 0
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `contestparticipation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `contest_id` INT NOT NULL,
    `contestant_id` INT NOT NULL,
    UNIQUE KEY `uid_contestpart_contest_9b3b20` (`contest_id`, `contestant_id`),
    CONSTRAINT `fk_contestp_contest_ff3cd3a5` FOREIGN KEY (`contest_id`) REFERENCES `contest` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_contestp_user_2f1b144b` FOREIGN KEY (`contestant_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `contesttaskpoints` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `_points` LONGTEXT NOT NULL,
    `participation_id` INT NOT NULL,
    `task_id` INT NOT NULL,
    UNIQUE KEY `uid_contesttask_task_id_14227b` (`task_id`, `participation_id`),
    CONSTRAINT `fk_contestt_contestp_dd926dd3` FOREIGN KEY (`participation_id`) REFERENCES `contestparticipation` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_contestt_task_328068ff` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `submission` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `time` DATETIME(6) NOT NULL,
    `language` VARCHAR(30) NOT NULL,
    `source_code` LONGTEXT NOT NULL,
    `verdict` VARCHAR(5) NOT NULL  DEFAULT 'pe',
    `score` DECIMAL(6,3) NOT NULL  DEFAULT 0,
    `_subtask_scores` LONGTEXT,
    `time_used` DECIMAL(5,3),
    `memory_used` DECIMAL(7,3),
    `first_solve` BOOL NOT NULL  DEFAULT 0,
    `author_id` INT NOT NULL,
    `contest_id` INT,
    `task_id` INT NOT NULL,
    CONSTRAINT `fk_submissi_user_774092e0` FOREIGN KEY (`author_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_submissi_contest_ef4c8722` FOREIGN KEY (`contest_id`) REFERENCES `contest` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_submissi_task_d0e9951a` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `testcaseresult` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `subtask` INT NOT NULL,
    `test_case` INT NOT NULL,
    `verdict` VARCHAR(5) NOT NULL,
    `score` DECIMAL(6,3) NOT NULL  DEFAULT 0,
    `time_used` DECIMAL(5,3) NOT NULL,
    `memory_used` DECIMAL(7,3) NOT NULL,
    `submission_id` INT NOT NULL,
    CONSTRAINT `fk_testcase_submissi_b0ace0b1` FOREIGN KEY (`submission_id`) REFERENCES `submission` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(20) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `contest_task` (
    `contest_id` INT NOT NULL,
    `task_id` INT NOT NULL,
    FOREIGN KEY (`contest_id`) REFERENCES `contest` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `task_user` (
    `task_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
