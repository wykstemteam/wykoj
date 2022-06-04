-- upgrade --
ALTER TABLE `contest` ADD `publish_editorial` BOOL NOT NULL  DEFAULT 0;
ALTER TABLE `contest` ADD `editorial_content` LONGTEXT NOT NULL;
-- downgrade --
ALTER TABLE `contest` DROP COLUMN `publish_editorial`;
ALTER TABLE `contest` DROP COLUMN `editorial_content`;
