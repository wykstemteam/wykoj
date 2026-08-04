-- upgrade --
ALTER TABLE `task` ADD `allow_download` BOOL NOT NULL  DEFAULT 0;
-- downgrade --
ALTER TABLE `task` DROP COLUMN `allow_download`;
