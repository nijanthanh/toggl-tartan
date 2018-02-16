create database toggltartan;

use toggltartan;

create table `users`(
    id INT NULL AUTO_INCREMENT,
    api_token VARCHAR(45) NULL,
    toggl_id BIGINT NULL,
    email VARCHAR(100) NULL,
    name VARCHAR(100) NULL,
    date_created DateTime,
    date_updated DateTime,
    PRIMARY KEY (`id`)
);

create table `events`(
    id BIGINT NULL AUTO_INCREMENT,
    user_id INT NULL,
    is_active TINYINT DEFAULT 1,
    course_id VARCHAR(10) NULL,
    start_time Time,
    duration INT NULL,
    frequency VARCHAR(20) NULL, /* Possible values are onetime, weekly, monthly */
    from_date Date,
    till_date Date,
    monday boolean default false,
    tuesday boolean default false,
    wednesday boolean default false,

    PRIMARY KEY (`id`)
);