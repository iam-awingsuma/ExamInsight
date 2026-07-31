// GitHub repository information
const repo = "iam-awingsuma/ExamInsight";


// Repository stats
fetch(`https://api.github.com/repos/${repo}`)
.then(res=>res.json())
.then(data=>{

// Update the repository stats in the HTML
document.getElementById("stars").textContent=data.stargazers_count;
// Update the repository stats in the HTML
document.getElementById("forks").textContent=data.forks_count;
// Update the repository stats in the HTML
document.getElementById("watchers").textContent=data.watchers_count;

});


// Commit feed
fetch(`https://api.github.com/repos/${repo}/commits?sha=master`)
.then(res=>res.json())
.then(data=>{
// Get the container for commits
const container=document.getElementById("commits");
// Initialize an array to hold the commit dates for the chart
const labels=[];

// Display the latest 20 commits
data.slice(0,20).forEach(commit=>{
// Create a new div for each commit
const div=document.createElement("div");
// Set the class name for styling
div.className="commit";
// Set the inner HTML of the div to display commit message, author, and date
div.innerHTML=`
<b>${commit.commit.message}</b><br>
${commit.commit.author.name} • 
${new Date(commit.commit.author.date).toLocaleString()}
`;

container.appendChild(div); // Add the commit div to the container

labels.push(new Date(commit.commit.author.date).toLocaleDateString()); // Add the commit date to the labels array for the chart

});

// Get the context for the commit chart
const ctx=document.getElementById("commitChart");

// Create a line chart for commits over time
new Chart(ctx,{
type:'line',
data:{
labels:labels.reverse(),
datasets:[{
label:'Commits',
data:new Array(labels.length).fill(1),
borderColor:'#2563eb',
fill:false
}]
}
});

});




// Contributors
fetch(`https://api.github.com/repos/${repo}/contributors`)
.then(res=>res.json())
.then(data=>{

// Get the container for contributors
const container=document.getElementById("contributors");

// Display the contributors
data.forEach(user=>{

const div=document.createElement("div"); // Create a new div for each contributor

div.innerHTML=`👤 ${user.login} — ${user.contributions} commits`; // Set the inner HTML to display contributor's username and number of commits

container.appendChild(div); // Add the contributor div to the container

});

});