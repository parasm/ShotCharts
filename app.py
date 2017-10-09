from flask import Flask, render_template, request, redirect, make_response
import jinja2
import os
import requests
import matplotlib.pyplot as plt
import seaborn as sns
from nba_py import shotchart, player, team
from matplotlib.patches import Circle, Rectangle, Arc
import urllib.request
import datetime
from io import BytesIO
import random
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.offsetbox import  OffsetImage
import json


def draw_court(ax=None, color='black', lw=2, outer_lines=False):
	# If an axes object isn't provided to plot onto, just get current one
	if ax is None:
	    ax = plt.gca()

	# Create the various parts of an NBA basketball court

	# Create the basketball hoop
	# Diameter of a hoop is 18" so it has a radius of 9", which is a value
	# 7.5 in our coordinate system
	hoop = Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False)

	# Create backboard
	backboard = Rectangle((-30, -7.5), 60, -1, linewidth=lw, color=color)

	# The paint
	# Create the outer box 0f the paint, width=16ft, height=19ft
	outer_box = Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color,
	                      fill=False)
	# Create the inner box of the paint, widt=12ft, height=19ft
	inner_box = Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color,
	                      fill=False)

	# Create free throw top arc
	top_free_throw = Arc((0, 142.5), 120, 120, theta1=0, theta2=180,
	                     linewidth=lw, color=color, fill=False)
	# Create free throw bottom arc
	bottom_free_throw = Arc((0, 142.5), 120, 120, theta1=180, theta2=0,
	                        linewidth=lw, color=color, linestyle='dashed')
	# Restricted Zone, it is an arc with 4ft radius from center of the hoop
	restricted = Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw,
	                 color=color)

	# Three point line
	# Create the side 3pt lines, they are 14ft long before they begin to arc
	corner_three_a = Rectangle((-220, -47.5), 0, 140, linewidth=lw,
	                           color=color)
	corner_three_b = Rectangle((220, -47.5), 0, 140, linewidth=lw, color=color)
	# 3pt arc - center of arc will be the hoop, arc is 23'9" away from hoop
	# I just played around with the theta values until they lined up with the 
	# threes
	three_arc = Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw,
	                color=color)

	# Center Court
	center_outer_arc = Arc((0, 422.5), 120, 120, theta1=180, theta2=0,
	                       linewidth=lw, color=color)
	center_inner_arc = Arc((0, 422.5), 40, 40, theta1=180, theta2=0,
	                       linewidth=lw, color=color)

	# List of the court elements to be plotted onto the axes
	court_elements = [hoop, backboard, outer_box, inner_box, top_free_throw,
	                  bottom_free_throw, restricted, corner_three_a,
	                  corner_three_b, three_arc, center_outer_arc,
	                  center_inner_arc]

	if outer_lines:
	    # Draw the half court line, baseline and side out bound lines
	    outer_lines = Rectangle((-250, -47.5), 500, 470, linewidth=lw,
	                            color=color, fill=False)
	    court_elements.append(outer_lines)

	# Add the court elements onto the axes
	for element in court_elements:
	    ax.add_patch(element)

	return ax

def get_players():
	players = player.PlayerList()
	players_df = players.info()
	players_data = {}
	for index, row in players_df.iterrows():
		players_data[row['DISPLAY_FIRST_LAST']] = row['PERSON_ID']
	player_file = open('players.json','w')
	player_file.write(json.dumps(players_data))
	player_file.close()
    
    
def load_players():
	player_file = open('players.json','r')
	return json.load(player_file)

app = Flask(__name__)
player_data = load_players()

@app.route('/')
def hello():
	return render_template("index.html", players= player_data)

@app.route('/chart/<player_id>')
def player_shots(player_id):
	season = request.args.get('season')
	if not season:
		season = '2016-17'
	russ = shotchart.ShotChart(player_id=player_id, season=season)
	shot_df = russ.shot_chart()
	player_name = shot_df['PLAYER_NAME'][0]
	sns.set_style("white")
	sns.set_color_codes()
	pic = urllib.request.urlretrieve("http://stats.nba.com/media/players/230x185/"+player_id+".png",player_id+".png")
	harden_pic = plt.imread(pic[0])
	fig = plt.figure(figsize=(12,11))
	plt.scatter(shot_df.LOC_X, shot_df.LOC_Y)
	draw_court()
	# Adjust plot limits to just fit in half court
	plt.xlim(-250,250)
	# Descending values along th y axis from bottom to top
	# in order to place the hoop by the top of plot
	plt.ylim(422.5, -47.5)
	# get rid of axis tick labels
	# plt.tick_params(labelbottom=False, labelleft=False)
	plt.title(player_name+' FGA - '+season, y=1.01, fontsize=18)

	img = OffsetImage(harden_pic, zoom=0.6)
	img.set_offset((850,200))
	ax = plt.gca()
	ax.add_artist(img)
	ax.set_xlabel('')
	ax.set_ylabel('')
	#plt.show()
	canvas=FigureCanvas(fig)
	png_output = BytesIO()
	canvas.print_png(png_output)
	response=make_response(png_output.getvalue())
	response.headers['Content-Type'] = 'image/png'
	return response
	#return render_template("index.html")
def made_shots(team_shot_chart_df):
    """returns the shotchart of only made shots"""
    team_made_shot_df= team_shot_chart_df[team_shot_chart_df.SHOT_MADE_FLAG == 1]
    return team_made_shot_df
 
def missed_shots(team_shot_chart_df):
    """returns the shotchart of only missed shots"""
    team_missed_shot_df= team_shot_chart_df[team_shot_chart_df.SHOT_MADE_FLAG == 0]
    return team_missed_shot_df    
    
    
@app.route('/chart/<team_id>')
def team_shots(team_id):
    #What if more args are given like last_n games, a date,etc?
	season = request.args.get('season')
	if not season:
		season = '2016-17'
	team_shots = shotchart.ShotChart(player_id=0,team_id = team_id, season=season)
	team_shots_df = team_shots.shot_chart()
	sns.set_style("white")
	sns.set_color_codes()
	#pic = urllib.request.urlretrieve("http://stats.nba.com/media/teams/230x185/"+team_id+".png",team_id+".png")
	harden_pic = plt.imread(pic[0])
	fig = plt.figure(figsize=(12,11))
    team_missed = missed_shots(teamshots_df)
    team_made = made_shots(teamshots_df)
	plt.scatter(team_made.LOC_X, team_made.LOC_Y, marker = 'o')
    plt.scatter(team_missed.LOC_X, team_missed.LOC_Y, marker = 'x')
	draw_court()
	# Adjust plot limits to just fit in half court
	plt.xlim(-250,250)
	# Descending values along th y axis from bottom to top
	# in order to place the hoop by the top of plot
	plt.ylim(422.5, -47.5)
	# get rid of axis tick labels
	# plt.tick_params(labelbottom=False, labelleft=False)
	plt.titleteam_name+' FGA - '+season, y=1.01, fontsize=18)

	img = OffsetImage(harden_pic, zoom=0.6)
	img.set_offset((850,200))
	ax = plt.gca()
	ax.add_artist(img)
	ax.set_xlabel('')
	ax.set_ylabel('')
	#plt.show()
	canvas=FigureCanvas(fig)
	png_output = BytesIO()
	canvas.print_png(png_output)
	response=make_response(png_output.getvalue())
	response.headers['Content-Type'] = 'image/png'
	return response
	#return render_template("index.html")    
    
    
    
if __name__ == '__main__':
	port = int(os.environ.get('PORT', 8000))
	app.run(host='0.0.0.0', port=port,debug=True)