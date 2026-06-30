#version 330 core
in vec3 FragPos;
in vec3 Normal;
in vec3 VertexColor;
in vec2 TexCoord;
out vec4 FragColor;
uniform vec3 objectColor;
uniform bool useVertexColor;
uniform bool useTexture;
uniform sampler2D objectTexture;
uniform vec3 lightColor;
uniform vec3 lightPos;
uniform vec3 viewPos;
void main()
{
    vec3 baseColor;
    if (useTexture) {
        baseColor = texture(objectTexture, TexCoord).rgb;
    } else if (useVertexColor) {
        baseColor = VertexColor;
    } else {
        baseColor = objectColor;
    }
    float ambientStrength = 0.35;
    vec3 ambient = ambientStrength * lightColor;
    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    float specularStrength = 0.5;
    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
    vec3 specular = useTexture ? vec3(0.0) : specularStrength * spec * lightColor;
    vec3 result = (ambient + diffuse + specular) * baseColor;
    FragColor = vec4(result, 1.0);
}
