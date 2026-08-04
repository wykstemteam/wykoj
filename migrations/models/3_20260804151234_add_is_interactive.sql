-- upgrade --
ALTER TABLE `task` ADD `is_interactive` BOOL NOT NULL  DEFAULT 0;
-- downgrade --
ALTER TABLE `task` DROP COLUMN `is_interactive`;
