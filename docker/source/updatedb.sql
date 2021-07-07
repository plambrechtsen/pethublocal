ALTER TABLE devices ADD COLUMN custommode INTEGER;

UPDATE devices SET custommode=0;

