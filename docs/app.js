const repo = "iam-awingsuma/ExamInsight";


// Repository stats
fetch(`https://api.github.com/repos/${repo}`)
.then(res=>res.json())
.then(data=>{

document.getElementById("stars").textContent=data.stargazers_count;

document.getElementById("forks").textContent=data.forks_count;

document.getElementById("watchers").textContent=data.watchers_count;

});



// Commit feed
fetch(`https://api.github.com/repos/${repo}/commits?sha=master`)
.then(res=>res.json())
.then(data=>{

const container=document.getElementById("commits");

const labels=[];

data.slice(0,20).forEach(commit=>{

const div=document.createElement("div");

div.className="commit";

div.innerHTML=`
<b>${commit.commit.message}</b><br>
${commit.commit.author.name} • 
${new Date(commit.commit.author.date).toLocaleString()}
`;

container.appendChild(div);

labels.push(new Date(commit.commit.author.date).toLocaleDateString());

});


const ctx=document.getElementById("commitChart");

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

const container=document.getElementById("contributors");

data.forEach(user=>{

const div=document.createElement("div");

div.innerHTML=`👤 ${user.login} — ${user.contributions} commits`;

container.appendChild(div);

});

});