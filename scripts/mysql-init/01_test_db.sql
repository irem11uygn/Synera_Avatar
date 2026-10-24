-- MySQL konteyneri İLK kez kurulurken çalışır (docker-entrypoint-initdb.d).
-- Otomatik testler geliştirme/demo verisine dokunmasın diye ayrı bir veritabanı açar.
CREATE DATABASE IF NOT EXISTS avatar_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON avatar_test.* TO 'avatar'@'%';
