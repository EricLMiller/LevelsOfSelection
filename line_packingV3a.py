#!/usr/bin/python3
## Written by C. Williams 8/2021

import random
import sys
import numpy
import time
import csv
import math
import os.path
from datetime import datetime

def chooseFromWeight(list, list_of_weights): #chooses ONE list item based on a corresponding ORDERED list of weights/probabilites (e.g. choosing from items [A, B, C, D] with weights [1, 4, 3, 2] (e.g. probability [0.1, 0.4, 0.3, 0.2]))
	#here we will convert the list of weights into a list of "ranges," against which a random number can be checked (e.g. [1, 4, 3, 2] to [1, 5, 8, 10])
	ordered_list_of_weights=[list_of_weights[0]] #this sets up the first item in ordered_list_of_weights
	for i in range(1, len(list_of_weights)): #NOTE: this starts at 1 because the first element of ordered_list_of_weights has been established
		ordered_list_of_weights.append(list_of_weights[i]+ordered_list_of_weights[i-1])
	#print(list_of_weights)
	#print(ordered_list_of_weights)
	randvar=random.random()*sum(list_of_weights) #picks a random number between 0 and the sum of all weights
	for j in range(len(ordered_list_of_weights)): #checks that number to see what probability "range" its between; more literally, it sequentially checks whether its less than each value in the ordered list of probabilities and the first list item where that's true gets added.
		if randvar<ordered_list_of_weights[j]:
			return list[j]


def getCommunity(commGenData): #generates a community with a inidividuals from a uniformed distribution
	if commGenData["type_of_community"]=="uniform":
		community = [random.uniform(commGenData["min_length"], commGenData["max_length"]) for x in range(commGenData["size_of_community"])]
	elif commGenData["type_of_community"]=="homogeneous":
		community = [commGenData["length"] for x in range(commGenData["size_of_community"])]
	elif commGenData["type_of_community"]=="n-member":
		if len(commGenData["length_list"])!=len(commGenData["community_weight_list"]):
			print("Your lengthList and communityProportionList do not have the same number of members. Please check!")
			sys.exit()
		community=[]
		for j in range(len(commGenData["length_list"])): #itterates n times until each of the n lengths has been added
			for i in range(int(commGenData["size_of_community"]*commGenData["community_weight_list"][j])): #appends the community list with the minimum number of segment of length j
				community.append(commGenData["length_list"][j])
		if commGenData["size_of_community"]-len(community)>0:
			length_probability_list=[] #this will be the probabilities of each length, used to generate the correct community proportions on average 
			
			for j in range(0, len(commGenData["length_list"])): #generates the rest of the list with the correct probabilities for splitting up the remainder. NOTE: these are PROBABILITIES, not an ordered list of "ranges" from 0 to 1.
				length_probability_list.append((commGenData["community_weight_list"][j]*commGenData["size_of_community"]-int(commGenData["size_of_community"]*commGenData["community_weight_list"][j]))/(commGenData["size_of_community"]-len(community)))

			while len(community)<commGenData["size_of_community"]: #fills remaining spaces in community
				community.append(chooseFromWeight(commGenData["length_list"], length_probability_list))
	else:
		print("Incorrect starting community type entered. Please choose from uniform, homogeneous, or n-member.")
		sys.exit()
	return community #returns the community


def importGeneration(filename): #imports an existing generation from a csv file
	with open(filename,'r') as csvfile:
		generationfile=csv.reader(csvfile, quoting=csv.QUOTE_NONNUMERIC) #NOTE: this converts ALL non-quoted values to floats. Keep this in mind.
		generation = []
		for row in generationfile:
			if row: #this removes blank rows
				generation.append(row) 
	return generation




#the following mutation funtions differ only in the distribution on which mutations are generated
#NOTE: these modifies the community variable ITSELF, so be careful if you need to use the starting community later
def mutateCommunity(community, mutationData):
	number_of_mutations = numpy.random.binomial(len(community), mutationData["mutation_probability"]) #choose a number of elements to mutate based on a binomial distribution
	# --- Generate mutations
	if mutationData["mutation_type"]=="uniform":
		mutation_list = abs(numpy.random.uniform(mutationData["min_mutation_size"],mutationData["max_mutation_size"],number_of_mutations)) #generate POSITIVE mutations based on a uniformed distribution #NOT DISCRETE
	elif mutationData["mutation_type"]=="poisson":
		mutation_list = numpy.random.poisson(mutationData["mutation_mean_size"], number_of_mutations) #generates mutations based on a poisson distribution #this is, of course, inherently DISCRETE
	elif mutationData["mutation_type"]=="normal":
		mutation_list = abs(numpy.random.normal(0,mutationData["mutation_standard_deviation"],number_of_mutations)) #generates POSITIVE mutations based on a normal distribution 
		mutation_list = [round(x/mutationData["mutation_delta"])*mutationData["mutation_delta"] for x in mutation_list] #this converts all mutations to factors of mutation_delta (e.g. discretizies segment sizes)
	else:
		print("Incorrect mutation type entered. Please choose from uniform, homogeneous, or n-member.")
		sys.exit()
	mutation_list = [min(max(mutationData["min_mutation_size"], x), mutationData["max_mutation_size"]) for x in mutation_list] #caps all mutations
	# --- Choose individuals to mutate
	segments_to_mutate = random.sample(range(len(community)), number_of_mutations) #choose which elements will be mutated
	for j in range(number_of_mutations): #modifies the segments_to_mutate according to their chosen mutation
		community[segments_to_mutate[j]] = community[segments_to_mutate[j]] + random.choice((-1, 1))*mutation_list[j] #adds +/- the respective mutation
	culled_community=[x for x in community if x>=minSegmentSize and x<=maxSegmentSize] #this removes all line segments less than or equal to minSegmentSize (or rather, creates a new list only keeping positive valued ones)
	return culled_community


def fillIntervalInf(community, countmax=math.inf): #this function fills the interval with segments, by filling and then generating new gaps in the interval
	starts = [] #record of where line segments were successfully placed
	ends = [] #record of where line segments end
	gaps = [1] #records gaps available to place segments in
	list_of_segments=[] #sets up a (currently empty) list of segments which made it onto the community
	useable_community = numpy.array(community) #we will remove line segments from useable_community

	count = 0 #for when I wanna do count
	while any(numpy.array(gaps)>min(useable_community)): #while there's space for a segment in any of our gaps
		count = count+1 #for when I wanna do count
		placement = random.random() #pick a random point 
		if countmax==math.inf: #update placement to stay within range of plausible values, [0,1-x] where x is min length (ONLY FOR INFINITE)
			placement=placement*(1-min(useable_community))
		length = random.choice(useable_community) #pick a random length
		#print(length)
		if any(numpy.logical_and(numpy.array([0]+ends)<placement, placement<numpy.array([x-length for x in starts+[1]]))): #if point is within a valid placement, p in [ends, starts)
			starts.append(placement) #add the new placement to the list
			ends.append(placement+length)
			list_of_segments.append(length) #add successful segment length to list
			
			# Update gaps to account for new segment
			starts.sort()
			ends.sort()
			gaps = numpy.subtract(starts+[1], [0]+ends) #check size of gaps
			#print(gaps)

			if countmax==math.inf: # Update useable_community so we only try to place line segments that have a chance of fitting (ONLY FOR INFINITE)
				useable_community = useable_community[useable_community<max(gaps)]
			if len(useable_community)==0: #if there's no more useable communities
				break #quit early to prevent next step from breaking
			if countmax==math.inf and max(gaps)<2*min(useable_community): #if not running finite AND all remaining gaps can only fit at MOST one more segment
				useable_gaps = numpy.array(gaps)[numpy.array(gaps)>min(useable_community)] #select all gaps that can fit at least one segment
				#print(useable_gaps)
				#print(list_of_segments)
				for gap in useable_gaps: #for each viable gap
					useable_community_temp = useable_community[useable_community<gap] #select all useable segments FOR this gap
					useable_community_weight = [(gap-ind)/gap for ind in useable_community_temp] #calculate probability of placement for each segment
					x = chooseFromWeight(useable_community_temp, useable_community_weight) #choose a segment based on its weight
					list_of_segments.append(x) #append that segment to the list
				break #quit the loop early
		if count>=countmax:
			break
	return(list_of_segments) ###TOGGLE FOR COVERAGE
	#return(count) #for when I wanna do count ###TOGGLE FOR COUNT


def selectCommunitiesIndex(community_level_selection_toggle, successful_individual_generation, number_of_communities):
	next_generation_communities_index=[]
	if community_level_selection_toggle == True: #chooses the next generation based proportionally on how successful a community was
		weight_of_communities=[] #this will be filled with the "weigth" of each community, which will then determine how likely it is to pass into the next generation
		for successful_individual_community in successful_individual_generation: #sets the weight of each community by summing it
			weight_of_communities.append(sum(successful_individual_community))
		for i in range(number_of_communities): #this does the actual SELECTING of communities for the next generation. It loops through and chooses communities based on their weight, until the next generation has been filled with communities.
			next_generation_communities_index.append(chooseFromWeight(range(len(successful_individual_generation)), weight_of_communities)) #returns INDEX based on weight of communities
	else: #chooses the next generation at random
		for i in range(number_of_communities): #loops until enough communities have been chosen
			next_generation_communities_index.append(random.randrange(len(successful_individual_generation))) #chooses between the communities at random (RETURNS INDEX)
	return next_generation_communities_index

def selectIndividuals(individual_level_selection_toggle, individual_selection_type, generation, size_of_community):
	if individual_level_selection_toggle == True: #chooses individuals for the next generation based on how successfully they covered the line segment
		next_generation_individuals=[]
		for community in generation: #loops this process for each community in the inputted generation
			next_community=[] #this will become the newly generated commmunity of individuals
			#note: the weight of each individual is equal to their length; therefore, we can simply reuse community as the weights.
			for i in range(size_of_community): #this does the actual SELECTING of individuals for the next generation. It loops through and chooses individuals based on their proportion/weight, until a given next-gen-community has been filled with individuals.
				if individual_selection_type == "placement": #choose based on number of times placed on interval
					next_community.append(random.choice(community))
				elif individual_selection_type == "coverage2": #choose based on square of coverage
					community_weight=[x**2 for x in community]
					next_community.append(chooseFromWeight(community, community_weight))
				elif individual_selection_type == "coverage": #choose based coverage
					next_community.append(chooseFromWeight(community, community))
				else: #if I typed something wrong, stop everything
					sys.exit()
			next_generation_individuals.append(next_community) #adds the newly selected community to the next generation
	else: #chooses the next generation at random
		next_generation_individuals=[]
		for community in generation: #loops this process for each community in the inputted generation 
			next_community=[] #this will become the newly generated commmunity of individuals
			for i in range(size_of_community): #loops until enough individuals have been chosen
				next_community.append(random.choice(community)) #chooses between the individuals in a community at random
			next_generation_individuals.append(next_community) #adds the newly selected community to the next generation
	return next_generation_individuals



### COMPILIATION OF COMMANDS ### (uses global variables bc im lazy)
def iterateGenerations(starting_generation, number_of_generations): #This command iterates through generations of selection number_of_generations number of times
	# A little Sanity Checker (prints "percent complete")
	percent_done=[]
	numberoftimechecks=100
	for i in range(numberoftimechecks):
		percent_done.append(math.floor(number_of_generations/numberoftimechecks*(i+1)))
	#################################################################
	generation=starting_generation
	for i in range(number_of_generations): #Iterates through the generations number_of_generations times.
		# print(generation)
		start_time=time.time()
		if i%freqOfGenCollect==0: #once our index hits a multiple of freqOfGenCollect, write the generation to a file
			generationcsv = "generations_"+ run_label + "_" + str(i) + ".csv"
			with open(generationcsv, 'w') as csvfile: #writes the generation before selection ###Commented Out bc it takes up time
				csvwriter = csv.writer(csvfile)
				csvwriter.writerows(generation)
		#start_time_gen=time.time()
		successfulIndividualGeneration=[fillIntervalInf(community, numberOfAttempts) for community in generation] #fills a interval for each community in a generation, returning an array of the successfully placed individuals for each
		with open(coveragecsv, 'a') as csvfile: #writes the coverage of a community
			csvwriter = csv.writer(csvfile)
			csvwriter.writerow([sum(community) for community in successfulIndividualGeneration]) 
		# print(successfulIndividualGeneration)
		# print(sum(successfulIndividualGeneration[0])) #prints the length (e.g. weight) of first community's interval
		# print("Placement: "+str(time.time()-start_time)) #TIME CHECK
		
		nextGenerationCommunitiesIndex=selectCommunitiesIndex(communityLevelSelectionToggle, successfulIndividualGeneration, numberOfCommunities) #Selects numberOfCommunities communities (by index) for the next generation. See the selectCommunitiesIndex function for more details.
		# print("Community Index Select: "+str(time.time()-start_time)) #TIME CHECK
		if individualLevelSelectionToggle==True: #if we are selecting individiuals based on performance
			if numpy.any(numpy.array([len(successfulIndividualGeneration[i]) for i in nextGenerationCommunitiesIndex])==0): # ensure we don't pass an empty community
				nextGenerationCommunities=[None]*len(nextGenerationCommunitiesIndex)
				for n in range(len(nextGenerationCommunitiesIndex)):
					index = nextGenerationCommunitiesIndex[n]
					if successfulIndividualGeneration[index]==[]: # if selected community didn't place anything
						nextGenerationCommunities[n]=generation[index] # use the original community instead
					else:
						nextGenerationCommunities[n]=successfulIndividualGeneration[index]
			else:
				nextGenerationCommunities=[successfulIndividualGeneration[i] for i in nextGenerationCommunitiesIndex]
		else: # if we are selecting individuals based on drift
			nextGenerationCommunities=[generation[i] for i in nextGenerationCommunitiesIndex] #pass the original generation list
		# print("Community Select: "+str(time.time()-start_time)) #TIME CHECK
		
		nextGenerationIndividuals=selectIndividuals(individualLevelSelectionToggle, individualSelectionType, nextGenerationCommunities, commGenData["size_of_community"]) #Selects sizeOfCommunity individuals for the next generation. See the selectIndividiuals function for more details.
		# print("Individual Select: "+str(time.time()-start_time)) #TIME CHECK
		# print(nextGenerationIndividuals)
		mutatedGeneration=[mutateCommunity(community, mutationData) for community in nextGenerationIndividuals]
		# print("Mutations: "+str(time.time()-start_time)) #TIME CHECK
		# print(mutatedGeneration)
		generation=mutatedGeneration
		#################################################################
		if i in percent_done: #prints when we're X% done (just for my own sanity)
			print(str(math.floor((i+1)/number_of_generations*100)) + "% Percent Done!")
			print("Time of Most-Recent Run: "+str(time.time()-start_time))
		#end_time_gen=time.time()
		#print(end_time_gen-start_time_gen)
	#print(generation)



### Community Generation Variables ###
commGenData = {}
# !!! INPUTTED BY SYSTEM ARGUMENT !!! #
commGenData["type_of_community"]=sys.argv[5] #type of starting community (options: "uniform", "homogeneous", "n-member", or "from-csv")
# --- All Community
commGenData["size_of_community"]=int(sys.argv[9]) #number of segments in a community
# --- Uniform Community
commGenData["min_length"]=0.005 #minimum length of a segment in Uniformed Random Distribution community
commGenData["max_length"]=1 #maximum length of a segment in Uniformed Random Distribution community
# --- Homogeneous Community
if commGenData["type_of_community"]=="homogeneous":
	#commGenData["length"]=float(input("Input length of all community members (float between 0 and 1): ")) #length of a segment in a Homogeneous community
	commGenData["length"]=float(sys.argv[10])
	commGenData["type_of_community_label"]=commGenData["type_of_community"]+str(commGenData["length"])#.replace("0.","")
elif commGenData["type_of_community"]=="from-csv":
	commGenData["seed_csv"]=sys.argv[10]
	commGenData["seed_label"]=sys.argv[11]
	commGenData["type_of_community_label"]=commGenData["type_of_community"]+str(commGenData["seed_label"])#.replace("0.","")
else:
	commGenData["type_of_community_label"]=commGenData["type_of_community"]
# --- N-Membered Community
commGenData["length_list"]=[0.01, 0.877] #length of segments in an n member community
commGenData["community_weight_list"]=[0.5,0.5] #proportions of each segment-length in an n member community ***DOESEN'T WORK IF ONE HAS PROPORTION OF 0


### Mutation Variables ###
mutationData = {}
mutationData["mutation_type"]=sys.argv[6]
# ---Used for all mutation types
mutationData["mutation_probability"]=0.1 #probability of mutating any given line segment (used for ALL)
mutationData["min_mutation_size"]=0.001 #minimum allowed mutation size (used for ALL, optional for NORMAL/POISSON)
mutationData["max_mutation_size"]=0.1 #maximum allowed mutation size (used for ALL, optional for NORMAL/POISSON)
# ---Normal
mutationData["mutation_standard_deviation"]=0.005 #standard deviation of mutations (used for NORMAL)
mutationData["mutation_delta"]=0.001 #discretizes mutation size (used for NORMAL)
# ---Poisson
mutationData["mutation_mean_size"]=0.01 #mean size of a mutation (used for POISSON)

### Interval Placement Variables ###
minSegmentSize=0.005 #minimum allowable segment size (overall)
maxSegmentSize=1 #maximum allowable segment size (overall)
# !!! INPUTTED BY SYSTEM ARGUMENT !!! #
if sys.argv[3]=="inf":
	numberOfAttempts = math.inf
else:
	numberOfAttempts = int(sys.argv[3]) #this is the maximum number of times we will attempt to place a segment 

### Type of Program
# !!! INPUTTED BY SYSTEM ARGUMENT !!! #
individualLevelSelectionToggle = sys.argv[1].lower() == "true" #determines whether individual level selection happens
communityLevelSelectionToggle = sys.argv[2].lower() == "true" #determines whether community level selection happens

# !!! INPUTTED BY SYSTEM ARGUMENT !!! #
individualSelectionType = sys.argv[4] #type of individual level selection (options: "coverage", "coverage2", and "placement")
numberOfCommunities = int(sys.argv[8]) #the number of communities in a given generation (i.e. length of the array of generation)
# !!! INPUTTED BY SYSTEM ARGUMENT !!! #
numberOfGenerations = int(sys.argv[7])+1 #number of times the program will be run/looped through #its +1 so we collect generation files up to numberOfGenerations 

freqOfGenCollect = 25 #frequency with which to collect generational data

if individualLevelSelectionToggle == True:
	if communityLevelSelectionToggle == True:
		selectionType = "indcom"
	else:
		selectionType = "inddrf"
else:
	if communityLevelSelectionToggle == True:
		selectionType = "drfcom"
	else:
		selectionType = "drfdrf"


### Setting Up CSV Files ### 

# name based on the run-type
datetime_label = datetime.now().strftime("%Y%m%d_%H%M%S")
run_label = "_".join([str(numberOfAttempts), individualSelectionType, commGenData["type_of_community_label"], mutationData["mutation_type"],
	selectionType, str(numberOfGenerations-1), str(numberOfCommunities), str(commGenData["size_of_community"]), datetime_label])
coveragecsv = "coverage_" + run_label + ".csv"


with open(coveragecsv, 'w') as csvfile:  
    # creating a csv writer object  
    csvwriter = csv.writer(csvfile)  


### BEGIN PROGRAM ###

### TIME TEST ###
# #This tests how long it takes to walk through the iterateGenerations command. It will run through the commmand numberOfTimeTests times
# numberOfTimeTests = 10
# time_test=[]
# for i in range(numberOfTimeTests):
# 	start_time=time.time()
# 	iterateGenerations(1)
# 	# community = [getUniformRandomCommunity(sizeOfCommunity, minSizeStart, maxSizeStart) for i in range(10)]
# 	# selectIndividuals(individualLevelSelectionToggle, individualSelectionType, community, sizeOfCommunity)
# 	end_time=time.time()
# 	total_time=end_time-start_time
# 	print(total_time)
# 	time_test.append(total_time)
# print(time_test) #prints all the times of each set of iterations
# print(numpy.mean(time_test)) #prints the average time it takes to iterate generations numberOfGenerations times
# print(numpy.std(time_test))


### ITERATE GENERATIONS - MAIN PROGRAM ###
if commGenData["type_of_community"]=="from-csv":
	if os.path.exists(commGenData["seed_csv"]):
		startingGeneration=importGeneration(commGenData["seed_csv"])
	else:
		print("Seed does not exist.")
		sys.exit()

else:
	startingGeneration=[getCommunity(commGenData) for i in range(numberOfCommunities)]
iterateGenerations(startingGeneration, numberOfGenerations)


# successfulIndividualGeneration = [[1,1,1,1],[0.1,0.1,0.1,0.1],[0.2,0.2,0.2,0.2]]
# nextGenerationCommunitiesIndex=selectCommunitiesIndex(communityLevelSelectionToggle, successfulIndividualGeneration, numberOfCommunities) #Selects numberOfCommunities communities (by index) for the next generation. See the selectCommunitiesIndex function for more details.
# from pandas import Series
# print(Series.value_counts(nextGenerationCommunitiesIndex))





### Average Coverage of Uniformed Communities ###

# #length=math.floor(numberOfUnits*0.001) #for fillInterval
# length=0.001 #for fillIntervalInf

# percent_done=[]
# for i in range(10):
# 	percent_done.append(math.floor(numberOfGenerations/10*(i+1)))
# start_time=time.time()
# for i in range(numberOfGenerations):
# 	generation=[getHomogeneousCommunity(1, length) for i in range(numberOfCommunities)] #fills the generation array with numberOfCommunities communities
# 	#fills a interval for each community in a generation, returning an array of the successfully placed individuals for each
# 	#successfulIndividualGeneration=[fillInterval(community, numberOfUnits, numberOfAttempts) for community in generation] 	
# 	successfulIndividualGeneration=[fillIntervalInf(community) for community in generation] 
# 	with open(coveragecsv, 'a') as csvfile: #writes the coverage of a community
# 		csvwriter = csv.writer(csvfile)
# 		csvwriter.writerow([sum(community) for community in successfulIndividualGeneration]) #saves the coverage of the successful individuals to csv
# 	if i in percent_done: #prints when we're X% done (just for my own sanity)
# 		print(str(math.floor(i/numberOfGenerations*100)) + "% Percent Done!")
# end_time=time.time()
# total_time=end_time-start_time
# print(total_time)(base) eric@the-vac:/disks/home/corinne$ 
