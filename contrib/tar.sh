#!/bin/sh

tar -cvzf knockdaemon.tgz --exclude=knockdaemon/.git --exclude=knockdaemon/.idea --exclude=knockdaemon/build --exclude=knockdaemon/dist --exclude=knockdaemon/knockdaemon.egg-info --exclude=knockdaemon/knockdaemon_test --exclude=knockdaemon/labo --exclude=knockdaemon/salt knockdaemon/
