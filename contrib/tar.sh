#!/bin/sh

tar -cvzf knockdaemon2.tgz --exclude=knockdaemon2/.git --exclude=knockdaemon2/.idea --exclude=knockdaemon2/build --exclude=knockdaemon2/dist --exclude=knockdaemon2/knockdaemon2.egg-info --exclude=knockdaemon2/knockdaemon2_test --exclude=knockdaemon2/labo --exclude=knockdaemon2/salt knockdaemon2/
