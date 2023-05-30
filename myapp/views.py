from django.shortcuts import render, redirect
from django.http import HttpResponseServerError, HttpResponseNotFound
from .models import JobListing, User
from .forms import JobListingForm, UserForm
import io, re, os
import pdfplumber
import openai
import firebase_admin
from firebase_admin import credentials, firestore
from langchain.chains.summarize import load_summarize_chain
from langchain import OpenAI, PromptTemplate
from langchain.document_loaders import PyPDFLoader
from langchain.chains.llm import LLMChain
from django.urls import reverse
import config
cred = credentials.Certificate("/Users/knowhrishi/Documents/Code/Hackathons/HackBay23/resume_res/imployz-f8ee4-firebase-adminsdk-ei5aq-d9d56ea9fc.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
# openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.api_key = "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"


def extract_text_from_pdf(file_path_or_bytes):
    try:
        if isinstance(file_path_or_bytes, bytes):
            # It's bytes, make a file-like object out of it
            file = io.BytesIO(file_path_or_bytes)
        else:
            # It's a path, just open it normally
            file = open(file_path_or_bytes, 'rb')

        with pdfplumber.open(file) as pdf:
            text = ''.join(page.extract_text() for page in pdf.pages)
        return text
    except Exception as e:
        print(f"An error occurred while extracting text from pdf: {str(e)}")
        return None

def analyze_resume(resume_text, job_description, job_title):
    llm = OpenAI(temperature=0.7, openai_api_key=openai.api_key)

    # Define the prompt templates with input variables
    skills_template = PromptTemplate(input_variables=["resume_text"], template="Extract the skills from the resume:\n\n{resume_text}\n\nSkills:")
    compare_template = PromptTemplate(input_variables=["resume_skills", "job_description"], template="Compare the skills in the resume and job description:\n\nResume skills: {resume_skills}\n\nJob description:\n{job_description}\n\nAverage similarity score out of 100%:")
    links_template = PromptTemplate(input_variables=["resume_text"], template="Fetch Linkedin and Github link from the resume:\n\n{resume_text}\n\nGithub: \n LinkedIn:")
    overqualified_template = PromptTemplate(input_variables=["resume_text", "job_description"], template="Check if the candidate's qualifications are overfitting for the job. Reason: {resume_text} Job description: {job_description}, if overqualified, suggest a new job title.")

    # Create the chains
    skills_chain = LLMChain(llm=llm, prompt=skills_template)
    compare_chain = LLMChain(llm=llm, prompt=compare_template)
    links_chain = LLMChain(llm=llm, prompt=links_template)
    overqualified_chain = LLMChain(llm=llm, prompt=overqualified_template)

    # Run the chains
    extracted_skills = skills_chain.run({"resume_text": resume_text})
    similarity_score = compare_chain.run({"resume_skills": extracted_skills, "job_description": job_description})
    links = links_chain.run({"resume_text": resume_text})
    overqualification_check = overqualified_chain.run({"resume_text": resume_text, "job_description": job_description})
    
    # Extract the percentage from the AI response
    match = re.search(r"(\d+(?:\.\d+)?)%", similarity_score)
    similarity_score_inper = match.group(1) if match else "No score found"


    return {
        "skills": extracted_skills,
        "similarity_score": similarity_score,
        "links": links,
        "overqualification_check": overqualification_check,
        "similarity_score_inper": similarity_score_inper
    }

def summarize_pdf(pdf_file_path):
    llm = OpenAI(temperature=0)
    loader = PyPDFLoader(pdf_file_path)
    docs = loader.load_and_split()
    chain = load_summarize_chain(llm=llm, chain_type="map_reduce")
    return chain.run(docs)

def index(request):
    try:
        users_ref = db.collection(u'users')
        users = users_ref.get()
        users_data = [{'id': user.id, **user.to_dict()} for user in users]

        job_listings_ref = db.collection(u'joblistings')
        job_listings = job_listings_ref.stream()
        
        job_listings_data = [{'id': job_listing.id, **job_listing.to_dict()} for job_listing in job_listings]

        if request.method == 'POST':
            if 'joblisting_submit' in request.POST:
                joblisting_data = {
                    u'title': request.POST['title'],
                    u'description': request.POST['description']
                }
                db.collection(u'joblistings').document().set(joblisting_data)

            elif 'user_submit' in request.POST:
                user_data = {
                    u'name': request.POST['name'],
                    u'age': request.POST['age'],
                    u'email': request.POST['email'],
                    u'job_listing': request.POST['job_listing'],
                    u'resume': request.FILES['resume'].read()
                }
                
                print(f"{request.POST['job_listing']}")
                # Save the user data to Firestore and get the document ID
                user_doc = db.collection(u'users').document()
                user_doc.set(user_data)
                # Get the document ID and update the user_data dictionary
                user_data['id'] = user_doc.id
                # Get the job listing ID from the selected job listing
                job_listing_id = request.POST['job_listing']
                # Update the job_id field in the user document
                user_doc.update({ 'j_id': job_listing_id })
                job_listing_ref = db.collection('joblistings').document(job_listing_id)
                job_listing = job_listing_ref.get()
                user_doc.update({ 'job_listing': job_listing.to_dict()['title'] })

                return redirect(reverse('myapp:index'))

        context = {
            'users': users_data,
            'job_listings': job_listings_data,
        }

        return render(request, 'index.html', context)
    except Exception as e:
        print(f"An error occurred in the index view: {str(e)}")
        return HttpResponseServerError("An internal server error occurred.")



def user_detail(request, user_id):
  
    user_ref = db.collection(u'users').document(user_id)
    user = user_ref.get()
    if user.exists:
        user_data = user.to_dict()
        job_id = user_data.get('j_id')
        
        # Now get the job title using the job_id
        job_listing_ref = db.collection('joblistings').document(job_id)
        job_listing = job_listing_ref.get()
        # If the job listing exists, return the user data and job title
        if job_listing.exists:
            job_title = job_listing.to_dict()['title']
            job_description = job_listing.to_dict()['description']

            # Check if the user's document already has the analysis results
            if 'resume_skills' in user_data and 'comparison' in user_data and 'links' in user_data and 'overqualification_check' in user_data:
                # Results are already in the database, just fetch them
                results = {
                    'skills': user_data['resume_skills'],
                    'similarity_score': user_data['comparison'],
                    'links': user_data['links'],
                    'overqualification_check': user_data['overqualification_check'],
                    'similarity_score_inper': user_data['similarity_score_inper'],
                }
            else:
                # Perform the analysis and save the results to the database
                resume_text = extract_text_from_pdf(user_data.get('resume'))
                if resume_text is not None:
                    results = analyze_resume(resume_text, job_description, job_title)
                    if "skills" in results and "similarity_score" in results and "links" in results and "overqualification_check" in results:
                        user_ref.update({
                            'resume_skills': results["skills"],
                            'comparison': results["similarity_score"],
                            'links': results["links"],
                            'overqualification_check': results["overqualification_check"],
                            'similarity_score_inper': results["similarity_score_inper"],
                        })
                    else:
                        print("Incomplete results returned from analyze_resume")
                        return HttpResponseServerError("Incomplete results returned from analyze_resume")
                else:
                    print("Failed to extract text from the resume")
                    return HttpResponseServerError("Failed to extract text from the resume.")

            context = {
                'user': user_data,
                'resume_skills': results["skills"],
                'comparison': results["similarity_score"],
                'links': results["links"],
                'overqualification_check': results["overqualification_check"],
            }

            return render(request, 'user_detail.html', context)

        else:
            print(f"No job listing with id {job_id}")
            return HttpResponseNotFound("Job listing not found.")
    else:
        print(f"No user with id {user_id}")
        return HttpResponseNotFound("User not found.")